import Foundation

// MARK: - NetworkDecision

struct NetworkDecision: Codable {
    let allowConnection: Bool
    let requiredApn:     String?
    let forceVpn:        Bool
    let vpnEndpoint:     String?
    let quarantineMode:  Bool
    let telemetryOnly:   Bool
}

// MARK: - PolicyService

@MainActor
final class PolicyService: ObservableObject {

    static let shared = PolicyService()
    private init() {}

    @Published private(set) var decision: NetworkDecision?
    @Published private(set) var lastSync: Date?
    @Published private(set) var syncError: Error?

    private let session: URLSession = {
        let cfg = URLSessionConfiguration.default
        cfg.timeoutIntervalForRequest  = 10
        cfg.timeoutIntervalForResource = 30
        return URLSession(configuration: cfg)
    }()

    func sync() async {
        let posture = await PostureCollector.shared.collect()

        guard let endpoint = policyEndpoint() else { return }

        do {
            var request = URLRequest(url: endpoint)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("iOS", forHTTPHeaderField: "X-Device-Platform")
            request.httpBody = try JSONEncoder().encode(posture)

            let (data, response) = try await session.data(for: request)

            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }

            let dec = try JSONDecoder().decode(NetworkDecision.self, from: data)
            decision  = dec
            lastSync  = Date()
            syncError = nil

            if dec.forceVpn, let ep = dec.vpnEndpoint {
                await WireGuardService.shared.connect(to: ep)
            }
        } catch {
            syncError = error
        }
    }

    // MARK: Private

    private func policyEndpoint() -> URL? {
        // MDM-provisioned endpoint takes priority
        if let raw = UserDefaults.standard.string(forKey: "mihwar.policy_endpoint"),
           let url = URL(string: raw) {
            return url
        }
        return URL(string: "https://mihwar.qarar.sa/api/v1/policy/evaluate")
    }
}
