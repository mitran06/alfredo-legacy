"""Date and time parsing utilities for natural language input.

This module provides utilities to convert natural language dates and times
into ISO 8601 format for calendar operations.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
import re

from src.utils.logger import log_debug


def parse_natural_date(date_str: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    """Parse a natural language date string into a datetime object.
    
    Supports formats like:
    - "tomorrow", "today", "yesterday"
    - "next Monday", "this Friday"
    - "in 3 days", "in 2 weeks"
    - "January 15", "Jan 15 2025"
    - "2025-01-15"
    - "15/01/2025", "01/15/2025"
    
    Args:
        date_str: Natural language date string
        reference_date: Reference date for relative dates (defaults to now)
        
    Returns:
        Parsed datetime object, or None if parsing fails
    """
    if not date_str:
        return None
    
    date_str = date_str.lower().strip()
    ref_date = reference_date or datetime.now()
    
    # Handle relative keywords
    if date_str in ["today", "now"]:
        return ref_date
    
    if date_str == "tomorrow":
        return ref_date + timedelta(days=1)
    
    if date_str == "yesterday":
        return ref_date - timedelta(days=1)
    
    # Handle "next Monday", "this Friday", etc.
    weekday_match = re.match(r"(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", date_str)
    if weekday_match:
        modifier = weekday_match.group(1)
        weekday_name = weekday_match.group(2)
        target_weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(weekday_name)
        current_weekday = ref_date.weekday()
        
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0 or modifier == "next":
            days_ahead += 7
        
        return ref_date + timedelta(days=days_ahead)
    
    # Handle "in X days/weeks/months"
    relative_match = re.match(r"in\s+(\d+)\s+(day|days|week|weeks|month|months)", date_str)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        
        if "day" in unit:
            return ref_date + timedelta(days=amount)
        elif "week" in unit:
            return ref_date + timedelta(weeks=amount)
        elif "month" in unit:
            return ref_date + relativedelta(months=amount)
    
    # Try dateutil parser for standard formats
    try:
        parsed = dateutil_parser.parse(date_str, default=ref_date, fuzzy=True)
        log_debug(f"Parsed '{date_str}' as {parsed}")
        return parsed
    except (ValueError, TypeError) as e:
        log_debug(f"Failed to parse date '{date_str}': {e}")
        return None


def parse_time(time_str: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    """Parse a time string into a datetime object.
    
    Supports formats like:
    - "8 AM", "8:00 AM", "8:30 PM"
    - "14:00", "14:30"
    - "8", "14" (assumes 24-hour if >= 12, AM otherwise)
    
    Args:
        time_str: Time string
        reference_date: Base date to attach time to (defaults to today)
        
    Returns:
        Datetime object with parsed time, or None if parsing fails
    """
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    ref_date = reference_date or datetime.now()
    
    try:
        # Try parsing with dateutil
        parsed = dateutil_parser.parse(time_str, default=ref_date, fuzzy=True)
        
        # Replace date part with reference date, keep time
        result = ref_date.replace(
            hour=parsed.hour,
            minute=parsed.minute,
            second=0,
            microsecond=0
        )
        log_debug(f"Parsed time '{time_str}' as {result.strftime('%H:%M')}")
        return result
        
    except (ValueError, TypeError) as e:
        log_debug(f"Failed to parse time '{time_str}': {e}")
        return None


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Parse a duration string into a timedelta object.
    
    Supports formats like:
    - "30 minutes", "1 hour", "2 hours"
    - "1.5 hours", "90 minutes"
    - "1h", "30m", "1h30m"
    
    Args:
        duration_str: Duration string
        
    Returns:
        timedelta object, or None if parsing fails
    """
    if not duration_str:
        return None
    
    duration_str = duration_str.lower().strip()
    
    # Match patterns like "1 hour", "30 minutes", "1.5 hours"
    pattern = r"(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|h|minute|minutes|min|mins|m)"
    matches = re.findall(pattern, duration_str)
    
    if not matches:
        log_debug(f"No duration pattern found in '{duration_str}'")
        return None
    
    total_minutes = 0
    for amount, unit in matches:
        amount = float(amount)
        if unit in ["hour", "hours", "hr", "hrs", "h"]:
            total_minutes += amount * 60
        elif unit in ["minute", "minutes", "min", "mins", "m"]:
            total_minutes += amount
    
    result = timedelta(minutes=total_minutes)
    log_debug(f"Parsed duration '{duration_str}' as {result}")
    return result


def combine_date_and_time(date_obj: datetime, time_obj: datetime) -> datetime:
    """Combine a date and time into a single datetime object.
    
    Args:
        date_obj: Datetime with the desired date
        time_obj: Datetime with the desired time
        
    Returns:
        Combined datetime
    """
    return date_obj.replace(
        hour=time_obj.hour,
        minute=time_obj.minute,
        second=0,
        microsecond=0
    )


def to_iso_format(dt: datetime) -> str:
    """Convert datetime to ISO 8601 format for calendar API.
    
    Args:
        dt: Datetime object
        
    Returns:
        ISO 8601 formatted string (YYYY-MM-DDTHH:MM:SS)
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def parse_datetime_range(
    date_str: Optional[str],
    time_str: Optional[str],
    duration_str: Optional[str],
    end_time_str: Optional[str] = None,
    reference_date: Optional[datetime] = None
) -> Optional[Tuple[str, str]]:
    """Parse date, time, and duration into start/end ISO 8601 strings.
    
    Args:
        date_str: Natural language date (e.g., "tomorrow")
        time_str: Time string (e.g., "8 AM")
        duration_str: Duration (e.g., "1 hour") - used if no end_time
        end_time_str: End time (e.g., "9 AM") - overrides duration
        reference_date: Reference date for relative parsing
        
    Returns:
        Tuple of (start_iso, end_iso) or None if parsing fails
    """
    ref_date = reference_date or datetime.now()
    
    # Parse date
    if date_str:
        date_obj = parse_natural_date(date_str, ref_date)
        if not date_obj:
            log_debug(f"Failed to parse date: {date_str}")
            return None
    else:
        date_obj = ref_date
    
    # Parse start time
    if time_str:
        time_obj = parse_time(time_str, date_obj)
        if not time_obj:
            log_debug(f"Failed to parse time: {time_str}")
            return None
        start_dt = combine_date_and_time(date_obj, time_obj)
    else:
        start_dt = date_obj
    
    # Parse end time
    if end_time_str:
        end_time_obj = parse_time(end_time_str, date_obj)
        if not end_time_obj:
            log_debug(f"Failed to parse end time: {end_time_str}")
            return None
        end_dt = combine_date_and_time(date_obj, end_time_obj)
    elif duration_str:
        duration = parse_duration(duration_str)
        if not duration:
            log_debug(f"Failed to parse duration: {duration_str}")
            return None
        end_dt = start_dt + duration
    else:
        # Default duration: 1 hour
        end_dt = start_dt + timedelta(hours=1)
        log_debug("No duration or end time specified, defaulting to 1 hour")
    
    return (to_iso_format(start_dt), to_iso_format(end_dt))
