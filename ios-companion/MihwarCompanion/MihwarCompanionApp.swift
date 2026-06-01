import SwiftUI
import BackgroundTasks

@main
struct MihwarCompanionApp: App {

    @UIApplicationDelegateAdaptor(AppDelegate.self) var delegate

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(PolicyService.shared)
        }
    }
}

// MARK: - AppDelegate

final class AppDelegate: NSObject, UIApplicationDelegate {

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        registerBackgroundTasks()
        return true
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        Task { await PolicyService.shared.sync() }
    }

    // MARK: Background task registration

    private func registerBackgroundTasks() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: "sa.qarar.mihwar.posture-sync",
            using: nil
        ) { task in
            Task {
                await PolicyService.shared.sync()
                task.setTaskCompleted(success: true)
            }
        }
    }
}
