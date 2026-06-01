using System.Net.NetworkInformation;
using System.Security.Cryptography;

namespace MihwarAgent.Services;

public record DevicePosture(
    string   DeviceId,
    string   Platform,
    string   Version,
    bool     AttestationValid,
    string[] NetworkInterfaces,
    DateTimeOffset Timestamp,
    string   CountryCode,
    int      RiskScore
);

public sealed class TelemetryCollector
{
    private readonly string _deviceId;
    private readonly ILogger<TelemetryCollector> _logger;

    public TelemetryCollector(ILogger<TelemetryCollector> logger)
    {
        _logger   = logger;
        _deviceId = GetOrCreateDeviceId();
    }

    public Task<DevicePosture> CollectAsync()
    {
        var interfaces = NetworkInterface.GetAllNetworkInterfaces()
            .Where(ni => ni.OperationalStatus == OperationalStatus.Up)
            .Select(ni => ni.Name)
            .ToArray();

        var attestation = CheckTpmAttestation();

        var posture = new DevicePosture(
            DeviceId:          _deviceId,
            Platform:          "Windows",
            Version:           Environment.OSVersion.ToString(),
            AttestationValid:  attestation,
            NetworkInterfaces: interfaces,
            Timestamp:         DateTimeOffset.UtcNow,
            CountryCode:       "SA",
            RiskScore:         CalculateRisk(interfaces)
        );

        return Task.FromResult(posture);
    }

    private bool CheckTpmAttestation()
    {
        try
        {
            // Real path: Tbsip_Submit_Command / NCrypt TPM2 key
            // Simplified: presence check via registry sentinel
            var tpmKey = Microsoft.Win32.Registry.LocalMachine
                .OpenSubKey(@"SYSTEM\CurrentControlSet\Services\TPM");
            return tpmKey != null;
        }
        catch
        {
            _logger.LogWarning("TPM attestation unavailable — software fallback, elevated risk");
            return false;
        }
    }

    private static int CalculateRisk(string[] interfaces)
    {
        var risk = 0;
        if (interfaces.Any(i => i.Contains("Wi-Fi", StringComparison.OrdinalIgnoreCase)))
            risk += 20;
        if (!interfaces.Any(i => i.Contains("Cellular", StringComparison.OrdinalIgnoreCase)))
            risk += 30;
        return Math.Min(risk, 100);
    }

    private static string GetOrCreateDeviceId()
    {
        var dir  = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Mihwar");
        var path = Path.Combine(dir, "device.id");
        Directory.CreateDirectory(dir);

        if (File.Exists(path))
            return File.ReadAllText(path).Trim();

        var id = Convert.ToHexString(RandomNumberGenerator.GetBytes(16));
        File.WriteAllText(path, id);
        return id;
    }
}
