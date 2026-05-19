import SwiftUI

struct ContentView: View {

    @EnvironmentObject private var policy: PolicyService

    var body: some View {
        NavigationStack {
            List {
                Section("Sovereign Status") {
                    StatusRow(label: "Connection",
                              value: policy.decision?.allowConnection == true ? "Allowed" : "Restricted",
                              color: policy.decision?.allowConnection == true ? .green : .red)

                    StatusRow(label: "VPN",
                              value: policy.decision?.forceVpn == true ? "Active" : "Inactive",
                              color: policy.decision?.forceVpn == true ? .green : .orange)

                    StatusRow(label: "Mode",
                              value: policy.decision?.quarantineMode == true ? "Quarantine" : "Normal",
                              color: policy.decision?.quarantineMode == true ? .red : .green)
                }

                Section("Last Sync") {
                    if let last = policy.lastSync {
                        Text(last.formatted(date: .omitted, time: .standard))
                            .foregroundStyle(.secondary)
                    } else {
                        Text("Never").foregroundStyle(.secondary)
                    }
                }

                if let err = policy.syncError {
                    Section("Error") {
                        Text(err.localizedDescription)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Mihwar Agent")
            .toolbar {
                Button("Sync") {
                    Task { await policy.sync() }
                }
            }
            .refreshable {
                await policy.sync()
            }
        }
    }
}

private struct StatusRow: View {
    let label: String
    let value: String
    let color: Color

    var body: some View {
        HStack {
            Text(label)
            Spacer()
            Text(value).foregroundStyle(color).bold()
        }
    }
}
