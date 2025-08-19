# Async Architecture Migration Guide

## Overview

The PagodaLightPico system has been migrated from a synchronous blocking architecture to an asynchronous non-blocking architecture using MicroPython's `asyncio` module. This change resolves the ETIMEDOUT errors by preventing blocking operations.

## Key Changes

### 1. Main Loop Architecture
**Before (Synchronous):**
```python
while True:
    web_server.handle_requests(timeout=0.1)  # Blocking
    if time_to_update_pwm:
        update_pwm_pins()  # Blocking
    time.sleep(0.1)
```

**After (Asynchronous):**
```python
async def main():
    tasks = [
        asyncio.create_task(pwm_update_task()),
        asyncio.create_task(network_monitor_task()),
        asyncio.create_task(web_server.serve_forever())
    ]
    await asyncio.gather(*tasks)
```

### 2. Web Server
- **New file:** `lib/web_server_async.py`
- **Non-blocking:** Uses `setblocking(False)` on sockets
- **Concurrent:** Each client connection handled in separate async task
- **Efficient:** Yields control with `await asyncio.sleep()` to prevent blocking

### 3. Task Separation
The system now runs three concurrent async tasks:

1. **PWM Update Task:** Handles LED brightness updates
2. **Network Monitor Task:** Manages WiFi/MQTT reconnections
3. **Web Server Task:** Serves HTTP requests

## Benefits

### Eliminates Blocking Issues
- Web requests no longer block PWM updates
- PWM updates no longer block web requests
- Network operations don't freeze the system

### Better Resource Utilization
- CPU time shared efficiently between tasks
- Memory usage optimized with proper yielding
- Responsive to multiple simultaneous operations

### Improved Reliability
- Individual task failures don't crash the entire system
- Better error isolation and recovery
- Graceful handling of network timeouts

## Files Changed

### New Files
- `lib/web_server_async.py` - Async web server implementation
- `test_async.py` - Simple async functionality test
- `ASYNC_MIGRATION.md` - This migration guide

### Modified Files
- `main.py` - Complete rewrite with async architecture
- Removed dependency on old `lib/web_server.py`

## Testing the Migration

### 1. Test Async Support
Run the test script to verify asyncio works:
```python
# On the Pico W
exec(open('test_async.py').read())
```

### 2. Monitor System Behavior
After deployment, monitor logs for:
- `[WEB] Async server started on port 80`
- `Started X async tasks`
- No more ETIMEDOUT errors
- Smooth concurrent operations

### 3. Web Interface Testing
- Access the web interface while PWM updates are running
- Verify page loads quickly without timeouts
- Test multiple simultaneous browser connections

## Troubleshooting

### If Async Doesn't Work
If MicroPython version doesn't support asyncio:
1. Update MicroPython firmware to latest version
2. Verify Pico W has sufficient memory
3. Check for syntax errors in async/await usage

### Performance Issues
If system seems slow:
1. Adjust `await asyncio.sleep()` intervals
2. Monitor memory usage with `gc.mem_free()`
3. Reduce web server response size if needed

### Connection Issues
If web server doesn't start:
1. Check WiFi connection status
2. Verify port 80 is not blocked
3. Monitor async task creation logs

## Rollback Plan

If issues occur, you can temporarily rollback by:
1. Reverting `main.py` to previous synchronous version
2. Using old `lib/web_server.py` instead of async version
3. Removing async-specific imports and syntax

However, this will bring back the original ETIMEDOUT issues.

## Future Enhancements

The async architecture enables future improvements:
- WebSocket support for real-time updates
- Multiple concurrent web clients
- Background data logging
- Real-time sensor monitoring
- Advanced scheduling features

## Performance Expectations

With the async architecture:
- **Web Response Time:** < 1 second (vs. potential timeouts before)
- **PWM Update Accuracy:** Maintained precise timing
- **Memory Usage:** Similar or slightly better due to efficient yielding
- **CPU Usage:** More efficient sharing between tasks
- **Concurrent Connections:** Multiple web clients supported

The system should now be much more responsive and reliable, with no more random ETIMEDOUT errors.