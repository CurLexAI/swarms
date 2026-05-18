using System.Net.Http.Json;

namespace MihwarAgent.Services;

public sealed class PolicyEngineClient
{
    private readonly HttpClient _http;
    private readonly ILogger<PolicyEngineClient> _logger;

    public PolicyEngineClient(IConfiguration config, ILogger<PolicyEngineClient> logger)
    {
        _logger = logger;

        var endpoint = config["Mihwar:PolicyEndpoint"] ?? "https://mihwar.qarar.sa/api/v1/policy";

        var handler = new SocketsHttpHandler
        {
            EnableMultipleHttp2Connections = true,
            KeepAlivePingDelay             = TimeSpan.FromSeconds(60),
            KeepAlivePingTimeout           = TimeSpan.FromSeconds(30),
            PooledConnectionLifetime       = TimeSpan.FromMinutes(5),
        };

        _http = new HttpClient(handler) { BaseAddress = new Uri(endpoint) };
        _http.DefaultRequestHeaders.Add("X-Device-Platform", "Windows");
        _http.DefaultRequestHeaders.Add("X-Agent-Version",   "1.0.0");
        _http.Timeout = TimeSpan.FromSeconds(10);
    }

    public async Task<NetworkPolicy> FetchAsync(DevicePosture posture, CellularState cellular)
    {
        var request = new { posture, cellular, timestamp = DateTimeOffset.UtcNow };

        try
        {
            var response = await _http.PostAsJsonAsync("/evaluate", request);
            response.EnsureSuccessStatusCode();
            var policy = await response.Content.ReadFromJsonAsync<NetworkPolicy>();
            return policy ?? FailSecurePolicy();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Policy fetch failed — fail-secure quarantine applied");
            return FailSecurePolicy();
        }
    }

    private static NetworkPolicy FailSecurePolicy() =>
        new(AllowConnection: false, RequiredApn: null,
            ForceVpn: false, VpnEndpoint: null,
            QuarantineMode: true, TelemetryOnly: true);
}
