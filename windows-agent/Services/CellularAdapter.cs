namespace MihwarAgent.Services;

public record CellularState(
    bool     IsConnected,
    string?  ApnName,
    string?  Iccid,
    string?  Imsi,
    string?  MccMnc,
    int      SignalStrength,
    string[] AvailableNetworks
);

public sealed class CellularAdapter
{
    private readonly ILogger<CellularAdapter> _logger;

    public CellularAdapter(ILogger<CellularAdapter> logger) => _logger = logger;

    public async Task<CellularState> GetStateAsync()
    {
        try
        {
            return await QueryWindowsMobileBroadbandAsync();
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Cellular API unavailable — returning disconnected state");
            return new CellularState(false, null, null, null, null, 0, Array.Empty<string>());
        }
    }

    private async Task<CellularState> QueryWindowsMobileBroadbandAsync()
    {
        // Windows.Networking.NetworkOperators — privileged custom capability required
        // (com.microsoft.windows.networkoperators.allow)
        // This is a compile-time stub; real implementation uses WinRT projection.
        await Task.Yield();

        return new CellularState(
            IsConnected:       true,
            ApnName:           "qarar-sovereign",
            Iccid:             null,   // Populated from eSIM profile when privileged
            Imsi:              null,
            MccMnc:            "420",  // STC SA MCC-MNC
            SignalStrength:    -1,     // Requires MobileBroadband API privilege
            AvailableNetworks: Array.Empty<string>()
        );
    }
}
