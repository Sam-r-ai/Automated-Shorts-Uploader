from datetime import datetime, timedelta, timezone

def calculate_next_upload_time(last_upload_time=None):
    """
    Simplified version of the function for testing.
    Calculate the next upload time based on preferred schedule throughout the day.
    """
    # Define preferred upload times in local time (every 3 hours throughout the day)
    preferred_hours = [0, 3, 6, 9, 12, 15, 18, 21]  # 12am, 3am, 6am, 9am, 12pm, 3pm, 6pm, 9pm
    
    # Get current time in local timezone
    local_tz = datetime.now().astimezone().tzinfo
    now = datetime.now(local_tz)
    
    # Start generating slots from today
    current_date = now.date()
    
    # If we have a last upload time, start from its date
    if last_upload_time:
        print(f"Last upload time: {last_upload_time}")
        
        # First, find which hour slot the last upload was in
        last_hour = last_upload_time.hour
        
        # Find the next hour in our schedule
        next_hour = None
        next_day = False
        
        # Check if the last hour is in our schedule
        if last_hour in preferred_hours:
            # Find the next hour in the sequence
            index = preferred_hours.index(last_hour)
            if index < len(preferred_hours) - 1:
                # There's another slot today
                next_hour = preferred_hours[index + 1]
            else:
                # Move to the first slot tomorrow
                next_hour = preferred_hours[0]
                next_day = True
        else:
            # Find the next available hour
            for hour in preferred_hours:
                if hour > last_hour:
                    next_hour = hour
                    break
            
            # If no slot found today, use the first slot tomorrow
            if next_hour is None:
                next_hour = preferred_hours[0]
                next_day = True
        
        # Create the datetime for the next slot
        if next_day:
            next_date = last_upload_time.date() + timedelta(days=1)
        else:
            next_date = last_upload_time.date()
        
        next_slot = datetime(
            next_date.year,
            next_date.month,
            next_date.day,
            next_hour, 0, tzinfo=local_tz
        )
    else:
        # No last upload time, find the next available slot from now
        found = False
        
        # Try today's slots
        for hour in preferred_hours:
            potential_slot = datetime(
                current_date.year, 
                current_date.month, 
                current_date.day, 
                hour, 0, tzinfo=local_tz
            )
            # Need at least 15 minutes in the future
            if potential_slot > now + timedelta(minutes=15):
                next_slot = potential_slot
                found = True
                break
        
        # If no suitable slot today, use tomorrow's first slot
        if not found:
            next_day = current_date + timedelta(days=1)
            next_slot = datetime(
                next_day.year, 
                next_day.month, 
                next_day.day, 
                preferred_hours[0], 0, tzinfo=local_tz
            )
    
    print(f"Scheduled next upload for: {next_slot.strftime('%Y-%m-%d %H:%M:%S')} {local_tz}")
    return next_slot

def test_scheduling():
    """Test that the scheduling algorithm works correctly by simulating several uploads."""
    # Create a mock "last upload time" for testing
    test_date = datetime(2025, 6, 22, 9, 0, 0, tzinfo=datetime.now().astimezone().tzinfo)
    print(f"Starting test with mock last upload time: {test_date}")

    # Simulate multiple uploads to verify the pattern
    for i in range(20):
        # Get next upload time
        next_upload = calculate_next_upload_time(test_date)
        
        # Print the scheduled time
        print(f"Upload {i+1}: {next_upload.strftime('%Y-%m-%d %H:%M')} - Hour: {next_upload.hour}")
        
        # Set this as the last upload for the next iteration
        test_date = next_upload

if __name__ == "__main__":
    test_scheduling()
