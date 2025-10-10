"""Information extraction utilities for parsing user messages.

This module provides utilities to extract structured information (dates, times,
event details) from natural language user input.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from src.utils.date_parser import (
    parse_natural_date,
    parse_time,
    parse_duration,
    to_iso_format
)
from src.utils.logger import log_debug


@dataclass
class ExtractedInfo:
    """Container for extracted information from user message."""
    date: Optional[datetime] = None
    time: Optional[datetime] = None
    duration: Optional[timedelta] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    confidence: float = 0.0  # 0.0 to 1.0
    raw_values: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.raw_values is None:
            self.raw_values = {}


class InformationExtractor:
    """Extracts structured information from natural language text."""
    
    # Common event type keywords
    EVENT_KEYWORDS = {
        'meeting', 'appointment', 'call', 'session', 'class', 'lecture',
        'exam', 'test', 'quiz', 'interview', 'presentation', 'demo',
        'standup', 'review', 'lunch', 'dinner', 'breakfast', 'workout',
        'dentist', 'doctor', 'therapy'
    }
    
    # Time indicators
    TIME_PATTERNS = [
        r'\b(\d{1,2})\s*(am|pm|AM|PM)\b',
        r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)\b',
        r'\b(\d{1,2}):(\d{2})\b',
        r'\bat\s+(\d{1,2})\b',
    ]
    
    # Duration patterns
    DURATION_PATTERNS = [
        r'for\s+(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|h|minute|minutes|min|mins|m)',
        r'(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|h|minute|minutes|min|mins|m)',
    ]
    
    # Date patterns
    DATE_PATTERNS = [
        r'\b(today|tomorrow|yesterday)\b',
        r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\bin\s+(\d+)\s+(day|days|week|weeks)\b',
    ]
    
    def extract_from_message(self, message: str, current_date: Optional[datetime] = None) -> ExtractedInfo:
        """Extract all possible information from a user message.
        
        Args:
            message: User's natural language message
            current_date: Reference date for relative parsing
            
        Returns:
            ExtractedInfo with extracted data
        """
        message_lower = message.lower()
        ref_date = current_date or datetime.now()
        extracted = ExtractedInfo()
        
        # Extract date
        date_info = self._extract_date(message_lower, ref_date)
        if date_info:
            extracted.date = date_info
            extracted.raw_values['date_text'] = message_lower
        
        # Extract time
        time_info = self._extract_time(message_lower, ref_date)
        if time_info:
            extracted.time = time_info
            extracted.raw_values['time_text'] = message_lower
        
        # Extract duration
        duration_info = self._extract_duration(message_lower)
        if duration_info:
            extracted.duration = duration_info
            extracted.raw_values['duration_text'] = message_lower
        
        # Extract title/event type
        title_info = self._extract_title(message_lower, message)
        if title_info:
            extracted.title = title_info
        
        # Extract location
        location_info = self._extract_location(message)
        if location_info:
            extracted.location = location_info
        
        # Calculate confidence based on what we found
        extracted.confidence = self._calculate_confidence(extracted)
        
        log_debug(f"Extracted info: date={extracted.date}, time={extracted.time}, "
                 f"duration={extracted.duration}, title={extracted.title}, "
                 f"confidence={extracted.confidence:.2f}")
        
        return extracted
    
    def _extract_date(self, message: str, ref_date: datetime) -> Optional[datetime]:
        """Extract date from message.
        
        Args:
            message: Lowercase message text
            ref_date: Reference date
            
        Returns:
            Parsed datetime or None
        """
        # Try each date pattern
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                parsed = parse_natural_date(date_str, ref_date)
                if parsed:
                    return parsed
        
        # Try direct parsing with dateutil
        # Look for phrases that might contain dates
        date_phrases = re.findall(r'\b(?:on|for|at)?\s*([a-zA-Z]+\s+\d{1,2}(?:st|nd|rd|th)?)\b', message)
        for phrase in date_phrases:
            parsed = parse_natural_date(phrase, ref_date)
            if parsed:
                return parsed
        
        return None
    
    def _extract_time(self, message: str, ref_date: datetime) -> Optional[datetime]:
        """Extract time from message.
        
        Args:
            message: Lowercase message text
            ref_date: Reference date
            
        Returns:
            Datetime with time set, or None
        """
        # Try each time pattern
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                time_str = match.group(0)
                # Remove 'at' prefix if present
                time_str = re.sub(r'^\s*at\s+', '', time_str)
                parsed = parse_time(time_str, ref_date)
                if parsed:
                    return parsed
        
        return None
    
    def _extract_duration(self, message: str) -> Optional[timedelta]:
        """Extract duration from message.
        
        Args:
            message: Lowercase message text
            
        Returns:
            Timedelta or None
        """
        for pattern in self.DURATION_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                duration_str = match.group(0)
                # Remove 'for' prefix if present
                duration_str = re.sub(r'^\s*for\s+', '', duration_str)
                parsed = parse_duration(duration_str)
                if parsed:
                    return parsed
        
        return None
    
    def _extract_title(self, message_lower: str, message_original: str) -> Optional[str]:
        """Extract event title/subject from message.
        
        Args:
            message_lower: Lowercase message
            message_original: Original case message
            
        Returns:
            Event title or None
        """
        # Look for common phrases
        title_patterns = [
            r'(?:i have|i\'ve got|schedule|create|add)\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\s+on|\s+at|\s+for|\s+next|\s+tomorrow|\s+today|$)',
            r'([a-zA-Z\s]+?)\s+(?:appointment|meeting|session|class)',
            r'(?:my|the)\s+([a-zA-Z\s]+?)(?:\s+is|\s+starts|\s+at)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, message_lower)
            if match:
                title = match.group(1).strip()
                # Filter out noise words
                noise_words = {'a', 'an', 'the', 'my', 'i', 'have', 'got'}
                title_words = [w for w in title.split() if w not in noise_words]
                if title_words:
                    return ' '.join(title_words).title()
        
        # Check for event type keywords
        for keyword in self.EVENT_KEYWORDS:
            if keyword in message_lower:
                # Get context around the keyword
                pattern = rf'\b(\w+\s+)?{keyword}(\s+\w+)?\b'
                match = re.search(pattern, message_lower)
                if match:
                    return match.group(0).strip().title()
        
        return None
    
    def _extract_location(self, message: str) -> Optional[str]:
        """Extract location from message.
        
        Args:
            message: Original message text
            
        Returns:
            Location string or None
        """
        # Look for location indicators
        location_patterns = [
            r'(?:at|in|@)\s+([A-Z][a-zA-Z0-9\s,]+?)(?:\s+on|\s+at|\s+for|$)',
            r'location:?\s+([^\n]+)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) > 3:  # Avoid false positives
                    return location
        
        return None
    
    def _calculate_confidence(self, extracted: ExtractedInfo) -> float:
        """Calculate confidence score for extracted information.
        
        Args:
            extracted: ExtractedInfo object
            
        Returns:
            Confidence score 0.0 to 1.0
        """
        score = 0.0
        
        # Date extraction
        if extracted.date:
            score += 0.3
        
        # Time extraction
        if extracted.time:
            score += 0.3
        
        # Duration or end time
        if extracted.duration or extracted.end_time:
            score += 0.2
        
        # Title extraction
        if extracted.title:
            score += 0.15
        
        # Location extraction
        if extracted.location:
            score += 0.05
        
        return min(score, 1.0)
    
    def merge_extracted_info(
        self,
        existing: Dict[str, Any],
        new_info: ExtractedInfo,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Merge new extracted information with existing data.
        
        Args:
            existing: Existing collected data
            new_info: Newly extracted information
            current_date: Reference date for combining date+time
            
        Returns:
            Updated collected data
        """
        ref_date = current_date or datetime.now()
        updated = existing.copy()
        
        # Update title if found
        if new_info.title and 'summary' not in updated:
            updated['summary'] = new_info.title
        
        # Update date
        if new_info.date:
            updated['_date'] = new_info.date
        
        # Update time and combine with date if both present
        if new_info.time:
            updated['_time'] = new_info.time
        
        # If we have both date and time, create start datetime
        if '_date' in updated and '_time' in updated:
            date_obj = updated['_date']
            time_obj = updated['_time']
            combined = date_obj.replace(
                hour=time_obj.hour,
                minute=time_obj.minute,
                second=0,
                microsecond=0
            )
            updated['start'] = to_iso_format(combined)
        
        # Handle duration or end time
        if new_info.duration and 'start' in updated:
            start_dt = datetime.fromisoformat(updated['start'].replace('Z', ''))
            end_dt = start_dt + new_info.duration
            updated['end'] = to_iso_format(end_dt)
        
        # Update location
        if new_info.location:
            updated['location'] = new_info.location
        
        return updated
    
    def identify_missing_fields(
        self,
        collected_data: Dict[str, Any],
        required_fields: List[str]
    ) -> List[str]:
        """Identify which required fields are still missing.
        
        Args:
            collected_data: Currently collected data
            required_fields: List of required field names
            
        Returns:
            List of missing field names
        """
        missing = []
        for field in required_fields:
            if field not in collected_data or collected_data[field] is None:
                missing.append(field)
        return missing
