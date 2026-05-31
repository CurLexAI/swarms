package security

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

const (
	HeaderTimestamp = "X-Qarar-Timestamp"
	HeaderSignature = "X-Qarar-Signature"
	MaxSkewSeconds  = 300
)

// HMACMiddleware fail-closes protected Mihwar routes unless the caller signs the
// exact request body as: hex(HMAC-SHA256(secret, timestamp + "." + rawBody)).
func HMACMiddleware() gin.HandlerFunc {
	secret := strings.TrimSpace(os.Getenv("MIHWAR_HMAC_SECRET"))
	if secret == "" {
		panic("MIHWAR_HMAC_SECRET is required")
	}

	return func(c *gin.Context) {
		timestamp := c.GetHeader(HeaderTimestamp)
		signature := c.GetHeader(HeaderSignature)
		if timestamp == "" || signature == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing signature headers"})
			return
		}

		ts, err := strconv.ParseInt(timestamp, 10, 64)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid timestamp"})
			return
		}

		now := time.Now().Unix()
		if ts > now+MaxSkewSeconds || ts < now-MaxSkewSeconds {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "expired request"})
			return
		}

		body, err := io.ReadAll(c.Request.Body)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "failed to read body"})
			return
		}
		c.Request.Body = io.NopCloser(bytes.NewReader(body))

		mac := hmac.New(sha256.New, []byte(secret))
		mac.Write([]byte(timestamp))
		mac.Write([]byte("."))
		mac.Write(body)
		expected := hex.EncodeToString(mac.Sum(nil))
		if !hmac.Equal([]byte(expected), []byte(signature)) {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid signature"})
			return
		}

		c.Next()
	}
}
