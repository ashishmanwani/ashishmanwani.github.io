from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProxyModel:
    id: str                      # unique ID: md5(host:port:user)
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    protocol: str = "http"       # http | socks5

    # Scoring fields (stored in Redis HASH)
    success_count: int = 0
    fail_count: int = 0
    captcha_count: int = 0
    avg_response_ms: float = 0.0
    last_used_at: datetime | None = None
    last_failed_at: datetime | None = None
    is_banned: bool = False
    banned_until: datetime | None = None

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def as_dict(self) -> dict:
        return {"http": self.url, "https": self.url}

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5  # neutral score for untested proxies
        return self.success_count / total

    def composite_score(self) -> float:
        """
        Higher score = better proxy.
        Weights: success rate (60%) + speed (30%) + captcha penalty (10%)
        """
        speed_score = max(0.0, 1.0 - (self.avg_response_ms / 10000))
        captcha_penalty = min(1.0, self.captcha_count * 0.1)
        return (
            0.60 * self.success_rate
            + 0.30 * speed_score
            - 0.10 * captcha_penalty
        )
