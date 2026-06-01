using System.Diagnostics;

namespace MihwarAgent.Services;

public record NetworkPolicy(
    bool    AllowConnection,
    string? RequiredApn,
    bool    ForceVpn,
    string? VpnEndpoint,
    bool    QuarantineMode,
    bool    TelemetryOnly
);

public sealed class NetworkEnforcer
{
    private readonly ILogger<NetworkEnforcer> _logger;
    private NetworkPolicy? _applied;

    public NetworkEnforcer(ILogger<NetworkEnforcer> logger) => _logger = logger;

    public async Task ApplyAsync(NetworkPolicy policy)
    {
        if (_applied == policy) return;

        _logger.LogInformation(
            "Applying policy: Allow={Allow} APN={Apn} VPN={Vpn} Quarantine={Quarantine}",
            policy.AllowConnection, policy.RequiredApn, policy.ForceVpn, policy.QuarantineMode);

        if (policy.QuarantineMode)
            await ApplyQuarantineAsync();
        else if (policy.AllowConnection)
            await AllowSovereignRouteAsync(policy);

        _applied = policy;
    }

    private async Task ApplyQuarantineAsync()
    {
        _logger.LogWarning("QUARANTINE: Blocking all non-telemetry outbound traffic");
        await RunPowerShellAsync(@"
            $existing = Get-NetFirewallRule -DisplayName 'Mihwar-Quarantine' -ErrorAction SilentlyContinue
            if (-not $existing) {
                New-NetFirewallRule -DisplayName 'Mihwar-Quarantine' `
                    -Direction Outbound -Action Block -Profile Any | Out-Null
            }
        ");
    }

    private async Task AllowSovereignRouteAsync(NetworkPolicy policy)
    {
        if (policy.ForceVpn && policy.VpnEndpoint is not null)
        {
            _logger.LogInformation("Configuring WireGuard tunnel to {Endpoint}", policy.VpnEndpoint);
            await WriteWireGuardConfigAsync(policy.VpnEndpoint);
        }

        await SetSovereignDnsAsync();
    }

    private async Task WriteWireGuardConfigAsync(string endpoint)
    {
        var dir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "WireGuard");

        if (!Directory.Exists(dir))
        {
            _logger.LogWarning("WireGuard not installed at {Dir} — skipping tunnel config", dir);
            return;
        }

        // Private key is generated per-device and stored in DPAPI-encrypted store.
        // Placeholder shows structure; real key loaded from credential manager.
        var config = $"""
            [Interface]
            # PrivateKey loaded from Windows Credential Manager at runtime
            Address = 10.200.200.2/24
            DNS = 10.200.200.1

            [Peer]
            # PublicKey fetched from Mihwar Core /api/v1/vpn/pubkey
            AllowedIPs = 0.0.0.0/0, ::/0
            Endpoint = {endpoint}:51820
            PersistentKeepalive = 25
            """;

        await File.WriteAllTextAsync(Path.Combine(dir, "qarar.conf"), config);
        _logger.LogInformation("WireGuard config written to {Dir}", dir);
    }

    private async Task SetSovereignDnsAsync()
    {
        await RunPowerShellAsync(
            "Get-NetAdapter | Where-Object { $_.Name -like '*Cellular*' } | " +
            "Set-DnsClientServerAddress -ServerAddresses '10.200.200.1'");
    }

    private async Task RunPowerShellAsync(string script)
    {
        var psi = new ProcessStartInfo
        {
            FileName               = "powershell.exe",
            Arguments              = $"-NonInteractive -ExecutionPolicy Bypass -Command \"{script}\"",
            UseShellExecute        = false,
            CreateNoWindow         = true,
            RedirectStandardError  = true,
            RedirectStandardOutput = true,
        };

        using var process = Process.Start(psi);
        if (process is null) return;

        await process.WaitForExitAsync();

        if (process.ExitCode != 0)
            _logger.LogWarning("PowerShell exited {Code}: {Err}",
                process.ExitCode, await process.StandardError.ReadToEndAsync());
    }
}
