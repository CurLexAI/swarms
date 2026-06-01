using MihwarAgent.Services;

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddWindowsService(options =>
    options.ServiceName = "Mihwar Sovereign Agent");

builder.Services.AddHostedService<AgentWorker>();
builder.Services.AddSingleton<TelemetryCollector>();
builder.Services.AddSingleton<CellularAdapter>();
builder.Services.AddSingleton<NetworkEnforcer>();
builder.Services.AddSingleton<QuicTransport>();
builder.Services.AddSingleton<PolicyEngineClient>();

builder.Logging.AddEventLog(settings =>
{
    settings.SourceName = "Mihwar Sovereign Agent";
});

var host = builder.Build();
host.Run();
