using System.Net;
using System.Net.Quic;
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;

namespace MihwarAgent.Services;

public sealed class QuicTransport : IAsyncDisposable
{
    private readonly ILogger<QuicTransport> _logger;
    private readonly string _host;
    private readonly int    _port;
    private QuicConnection? _connection;

    public QuicTransport(IConfiguration config, ILogger<QuicTransport> logger)
    {
        _logger = logger;
        var endpoint = config["Mihwar:Endpoint"] ?? "mihwar.qarar.sa:443";
        var parts    = endpoint.Split(':');
        _host = parts[0];
        _port = parts.Length > 1 ? int.Parse(parts[1]) : 443;
    }

    public async Task InitializeAsync(CancellationToken ct)
    {
        if (!QuicConnection.IsSupported)
        {
            _logger.LogWarning("QUIC not supported on this platform — telemetry via HTTP/2 fallback");
            return;
        }

        try
        {
            var options = new QuicClientConnectionOptions
            {
                RemoteEndPoint = new DnsEndPoint(_host, _port),
                ClientAuthenticationOptions = new SslClientAuthenticationOptions
                {
                    ApplicationProtocols = [new SslApplicationProtocol("mihwar-v1")],
                    EnabledSslProtocols  = System.Security.Authentication.SslProtocols.Tls13,
                    RemoteCertificateValidationCallback = ValidateServerCert,
                },
                DefaultStreamErrorCode = 0,
                DefaultCloseErrorCode  = 0,
                MaxInboundBidirectionalStreams  = 4,
                MaxInboundUnidirectionalStreams = 4,
            };

            _connection = await QuicConnection.ConnectAsync(options, ct);
            _logger.LogInformation("QUIC/TLS 1.3 connected to {Host}:{Port}", _host, _port);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "QUIC init failed — will retry on next cycle");
        }
    }

    public async Task SendAsync<T>(T data, CancellationToken ct = default)
    {
        if (_connection is null)
        {
            await InitializeAsync(ct);
            if (_connection is null) return;
        }

        try
        {
            await using var stream = await _connection.OpenOutboundStreamAsync(
                QuicStreamType.Unidirectional, ct);

            var bytes = JsonSerializer.SerializeToUtf8Bytes(data);
            await stream.WriteAsync(bytes, completeWrites: true, ct);
        }
        catch (QuicException ex)
        {
            _logger.LogWarning(ex, "QUIC stream error — resetting connection");
            await DisposeConnectionAsync();
        }
    }

    private static bool ValidateServerCert(
        object sender,
        X509Certificate? cert,
        X509Chain? chain,
        SslPolicyErrors errors)
    {
        // Production: pin sovereign CA thumbprint loaded from config
        return errors == SslPolicyErrors.None;
    }

    private async Task DisposeConnectionAsync()
    {
        if (_connection is not null)
        {
            await _connection.DisposeAsync();
            _connection = null;
        }
    }

    public async ValueTask DisposeAsync() => await DisposeConnectionAsync();
}
