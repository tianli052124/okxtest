import asyncio
import time
import collections
class RateLimiter(asyncio.Semaphore):
    """A custom semaphore to be used with REST API with velocity limit under asyncio"""

    def __init__(self, concurrency: int, interval: int):
        """控制REST API访问速率

        :param concurrency: API limit
        :param interval: Reset interval
        """
        super().__init__(concurrency)
        # Queue of inquiry timestamps
        self._inquiries = collections.deque(maxlen=concurrency)
        self._loop = asyncio.get_event_loop()
        self._concurrency = concurrency
        self._interval = interval
        self._count = concurrency

    def __repr__(self):
        return f"Rate limit: {self._concurrency} inquiries/{self._interval}s"

    async def acquire(self):
        await super().acquire()
        if self._count > 0:
            self._count -= 1
        else:
            timelapse = time.monotonic() - self._inquiries.popleft()
            # Wait until interval has passed since the first inquiry in queue returned.
            if timelapse < self._interval:
                await asyncio.sleep(self._interval - timelapse)
        return True

    def release(self):
        self._inquiries.append(time.monotonic())
        super().release()
