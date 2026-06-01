namespace MihwarAgent.Services;

public sealed class AgentWorker : BackgroundService
{
    private readonly TelemetryCollector _telemetry;
    private readonly CellularAdapter _cellular;
    private readonly NetworkEnforcer _enforcer;
    private readonly QuicTransport _quic;
    private readonly PolicyEngineClient _policy;
    private readonly ILogger<AgentWorker> _logger;

    public AgentWorker(
        TelemetryCollector telemetry,
        CellularAdapter cellular,
        NetworkEnforcer enforcer,
        QuicTransport quic,
        PolicyEngineClient policy,
        ILogger<AgentWorker> logger)
    {
        _telemetry = telemetry;
        _cellular  = cellular;
        _enforcer  = enforcer;
        _quic      = quic;
        _policy    = policy;
        _logger    = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Mihwar Agent started — Sovereign mode");

        await _quic.InitializeAsync(stoppingToken);

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var posture  = await _telemetry.CollectAsync();
                var cellular = await _cellular.GetStateAsync();
                var policy   = await _policy.FetchAsync(posture, cellular);

                await _enforcer.ApplyAsync(policy);
                await _quic.SendAsync(posture, stoppingToken);

                _logger.LogDebug("Cycle complete — next in 30s");
                await Task.Delay(TimeSpan.FromSeconds(30), stoppingToken);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Agent cycle failed — retrying in 5s");
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
        }

        _logger.LogInformation("Mihwar Agent stopped");
    }
}
