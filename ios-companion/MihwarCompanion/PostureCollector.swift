import Network
import UIKit

// MARK: - DevicePosture model

struct DevicePosture: Codable {
    let deviceId:          String
    let platform:          String
    let version:           String
    let batteryLevel:      Float
    let isCharging:        Bool
    let networkType:       String
    let vpnActive:         Bool
    let managedAppStatus:  String
    let timestamp:         String
    let countryCode:       String
    let riskScore:         Int
}

// MARK: - PostureCollector

final class PostureCollector {

    static let shared = PostureCollector()
    private init() {}

    func collect() async -> DevicePosture {
        UIDevice.current.isBatteryMonitoringEnabled = true

        let networkType = await resolveNetworkType()
        let vpn         = await isVPNActive()
        let managed     = checkManagedStatus()
        let risk        = calculateRisk(networkType: networkType, vpnActive: vpn)

        return DevicePosture(
            deviceId:         resolveDeviceId(),
            platform:         "iOS",
            version:          UIDevice.current.systemVersion,
            batteryLevel:     UIDevice.current.batteryLevel,
            isCharging:       UIDevice.current.batteryState == .charging,
            networkType:      networkType,
            vpnActive:        vpn,
            managedAppStatus: managed,
            timestamp:        ISO8601DateFormatter().string(from: Date()),
            countryCode:      "SA",
            riskScore:        risk
        )
    }

    // MARK: Private helpers

    private func resolveDeviceId() -> String {
        // MDM-provisioned ID takes priority
        if let mdmId = UserDefaults.standard.string(forKey: "mihwar.device_id") {
            return mdmId
        }
        // Stable per-installation ID (resets on erase)
        let key = "mihwar.install_id"
        if let existing = UserDefaults.standard.string(forKey: key) { return existing }
        let id = UUID().uuidString
        UserDefaults.standard.set(id, forKey: key)
        return id
    }

    private func resolveNetworkType() async -> String {
        await withCheckedContinuation { cont in
            let monitor = NWPathMonitor()
            monitor.pathUpdateHandler = { path in
                monitor.cancel()
                if path.usesInterfaceType(.cellular) { cont.resume(returning: "cellular") }
                else if path.usesInterfaceType(.wifi)  { cont.resume(returning: "wifi") }
                else                                   { cont.resume(returning: "other") }
            }
            monitor.start(queue: DispatchQueue.global())
        }
    }

    private func isVPNActive() async -> Bool {
        // Check for an active NEVPNManager tunnel named by our bundle ID
        await withCheckedContinuation { cont in
            NEVPNManager.shared().loadFromPreferences { _ in
                cont.resume(returning: NEVPNManager.shared().connection.status == .connected)
            }
        }
    }

    private func checkManagedStatus() -> String {
        // Apple DDM / ManagedAppConfig
        UserDefaults.standard.dictionary(forKey: "com.apple.configuration.managed") != nil
            ? "managed" : "unmanaged"
    }

    private func calculateRisk(networkType: String, vpnActive: Bool) -> Int {
        var risk = 0
        if networkType != "cellular" { risk += 25 }
        if !vpnActive               { risk += 30 }
        return min(risk, 100)
    }
}

// Bring NEVPNManager into scope without importing NetworkExtension at module level
import NetworkExtension
