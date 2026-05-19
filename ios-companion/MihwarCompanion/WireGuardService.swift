import Foundation
import NetworkExtension

// MARK: - WireGuardService

final class WireGuardService {

    static let shared = WireGuardService()
    private init() {}

    private let managerName = "Mihwar Sovereign VPN"

    /// Configure and start a WireGuard tunnel to the given endpoint.
    /// Requires a NETunnelProviderManager extension in the app bundle.
    func connect(to endpoint: String) async {
        do {
            let manager = try await loadOrCreate()
            configure(manager: manager, endpoint: endpoint)
            try await manager.saveToPreferences()
            try manager.connection.startVPNTunnel()
        } catch {
            // Log but never crash — VPN is an enforcement preference, not a hard blocker here
            print("[WireGuard] connect error: \(error)")
        }
    }

    // MARK: Private

    private func loadOrCreate() async throws -> NETunnelProviderManager {
        let managers = try await NETunnelProviderManager.loadAllFromPreferences()
        return managers.first(where: { $0.localizedDescription == managerName })
            ?? NETunnelProviderManager()
    }

    private func configure(manager: NETunnelProviderManager, endpoint: String) {
        let proto = NETunnelProviderProtocol()
        proto.serverAddress         = endpoint
        proto.providerBundleIdentifier = "sa.qarar.mihwar.companion.tunnel"

        // WireGuard config passed as providerConfiguration dict
        // (parsed by the NETunnelProvider extension using WireGuardKit)
        proto.providerConfiguration = [
            "wg-config": wgConfig(endpoint: endpoint)
        ]

        manager.protocolConfiguration  = proto
        manager.localizedDescription    = managerName
        manager.isEnabled               = true
    }

    private func wgConfig(endpoint: String) -> String {
        // Private key is generated once and stored in Keychain.
        // Public key is registered with Mihwar Core /api/v1/vpn/register.
        // Placeholder — real implementation uses WireGuardKit key generation.
        """
        [Interface]
        # PrivateKey = <loaded from Keychain>
        Address = 10.200.200.3/24
        DNS = 10.200.200.1

        [Peer]
        # PublicKey = <fetched from Mihwar Core>
        AllowedIPs = 0.0.0.0/0, ::/0
        Endpoint = \(endpoint):51820
        PersistentKeepalive = 25
        """
    }
}
