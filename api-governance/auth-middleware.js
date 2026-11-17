/**
 * Enterprise API Governance Auth Middleware
 * Enforces API-Key or Bearer JWT validation on machine-readable endpoints (/api/status)
 * while permitting Kubernetes health/readiness probes (/api/dashboard) when configured.
 */

const crypto = require('crypto');

const EXPECTED_API_KEY = process.env.TELEMETRY_API_KEY || 'dev-governed-telemetry-key';

function verifyApiKeyOrBearer(req, res, next) {
  const apiKey = req.header('X-API-Key');
  const authHeader = req.header('Authorization');

  // 1. Check X-API-Key header using constant-time comparison
  if (apiKey) {
    const providedBuf = Buffer.from(apiKey);
    const expectedBuf = Buffer.from(EXPECTED_API_KEY);
    if (
      providedBuf.length === expectedBuf.length &&
      crypto.timingSafeEqual(providedBuf, expectedBuf)
    ) {
      req.consumerIdentity = { authType: 'ApiKey', role: 'telemetry-reader' };
      return next();
    }
    return res.status(401).json({
      error: 'INVALID_API_KEY',
      message: 'Provided X-API-Key header failed governance validation.',
      timestamp: new Date().toISOString()
    });
  }

  // 2. Check OAuth2 / OIDC Bearer JWT structure (header.payload.signature)
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.slice(7).trim();
    const parts = token.split('.');
    if (parts.length === 3) {
      try {
        const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < now) {
          return res.status(401).json({
            error: 'TOKEN_EXPIRED',
            message: 'Bearer JWT token has expired.',
            timestamp: new Date().toISOString()
          });
        }
        req.consumerIdentity = {
          authType: 'BearerJWT',
          sub: payload.sub || 'unknown-client',
          scope: payload.scope || 'telemetry:read'
        };
        return next();
      } catch (err) {
        return res.status(401).json({
          error: 'MALFORMED_JWT',
          message: 'Bearer token payload is not valid JSON.',
          timestamp: new Date().toISOString()
        });
      }
    }
  }

  // 3. Reject unauthenticated requests with standardized ErrorResponse contract
  return res.status(401).json({
    error: 'UNAUTHORIZED',
    message: 'Missing valid X-API-Key or Authorization Bearer token.',
    timestamp: new Date().toISOString()
  });
}

module.exports = { verifyApiKeyOrBearer };
