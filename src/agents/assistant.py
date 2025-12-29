"""
Assistant Agent for ARCHER.

Provides general assistance, reminders, search, and communication management.
Enhanced with BaseSpecializedAgent capabilities including memory integration.
"""

import logging
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta

from src.llm.router import LLMRouter
from src.memory.semantic_memory import SemanticMemory
from src.events.bus import bus
from .base_specialized_agent import BaseSpecializedAgent

logger = logging.getLogger(__name__)


class AssistantAgent(BaseSpecializedAgent):
    """
    General-purpose assistant agent with enhanced capabilities.

    Features:
    - Context-aware reminders
    - Local activity search
    - Email/text monitoring and drafting
    - Calendar integration
    - Proactive suggestions
    - Memory integration (VectorMemory + EpisodicMemory)
    - Standardized handle() interface
    - Error handling and fallback strategies
    """

    def __init__(self, llm_router: LLMRouter, memory: SemanticMemory):
        # Initialize base class
        super().__init__(name="assistant", agent_id="assistant")
        
        # Set up LLM and semantic memory
        self.llm = llm_router
        self.semantic_memory = memory

        # Integrations
        self.email_enabled = os.getenv("EMAIL_INTEGRATION", "false").lower() == "true"
        self.calendar_enabled = (
            os.getenv("CALENDAR_INTEGRATION", "false").lower() == "true"
        )
        self.messaging_enabled = (
            os.getenv("MESSAGING_INTEGRATION", "false").lower() == "true"
        )

        # Reminder system
        self.reminders: List[Dict[str, Any]] = []
        self.last_reminder_check = datetime.now()

        # Subscribe to events
        bus.subscribe("voice.user_speech_end", self.process_user_query)
        bus.subscribe("vision.user.arrived", self.handle_user_arrival)

        logger.info("Enhanced Assistant Agent initialized with memory integration")

    def process_user_query(self, event_data: Dict[str, Any]):
        """Process general user queries."""
        text = event_data.get("text", "").lower()

        # Check for assistant keywords
        assistant_keywords = [
            "remind",
            "search",
            "email",
            "text",
            "calendar",
            "schedule",
        ]
        if any(keyword in text for keyword in assistant_keywords):
            logger.info("Assistant query detected")
            self.handle_assistant_query(text)

    def handle_assistant_query(self, query: str):
        """Handle assistant-related queries."""
        response = self.llm.get_response(
            query,
            role="assistant",
            context={"agent": "assistant", "capabilities": self.get_capabilities()},
        )

        # Check if response requires verification
        if self._requires_verification(response):
            if not self.llm.verify_action(f"Assistant action: {response}"):
                response = "I'm sorry, but I cannot perform that action due to safety verification."

        bus.publish("agent.assistant_response", {"response": response})

    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities."""
        return {
            "reminders": True,
            "search": True,
            "email_integration": self.email_enabled,
            "calendar_integration": self.calendar_enabled,
            "messaging_integration": self.messaging_enabled,
            "proactive_suggestions": True,
        }

    def _requires_verification(self, response: str) -> bool:
        """Check if response requires verification."""
        sensitive_actions = ["send email", "send text", "schedule", "remind"]
        return any(action in response.lower() for action in sensitive_actions)

    def handle_user_arrival(self, event_data: Dict[str, Any]):
        """Handle user arrival for proactive assistance."""
        # Check for pending reminders
        self.check_reminders()

        # Provide proactive suggestions
        self.provide_proactive_help()

    def check_reminders(self):
        """Check and announce pending reminders."""
        now = datetime.now()
        pending = [r for r in self.reminders if r["time"] <= now]

        for reminder in pending:
            bus.publish("agent.reminder_due", {"reminder": reminder})
            self.reminders.remove(reminder)

    def provide_proactive_help(self):
        """Provide context-aware proactive assistance."""
        # Get user context
        context = self.memory.get_context_for_llm()

        # Generate proactive suggestion
        prompt = "Based on user context and current time, suggest one helpful action or reminder."

        suggestion = self.llm.get_response(prompt, context=context, role="proactive")

        if suggestion and len(suggestion.strip()) > 10:
            bus.publish("agent.proactive_suggestion", {"suggestion": suggestion})

    def add_reminder(self, description: str, time: datetime):
        """Add a reminder."""
        reminder = {"description": description, "time": time, "created": datetime.now()}
        self.reminders.append(reminder)
        logger.info(f"Reminder added: {description} at {time}")

    def search_local_activities(self, query: str) -> List[Dict[str, Any]]:
        """Search for local activities (placeholder)."""
        # Placeholder - would integrate with local APIs
        return [{"name": "Sample Activity", "description": "Placeholder result"}]

    def monitor_communications(self):
        """Monitor email and messages."""
        if not (self.email_enabled or self.messaging_enabled):
            return

        try:
            # Check email
            if self.email_enabled:
                new_emails = self._check_email()
                if new_emails:
                    self._process_new_emails(new_emails)

            # Check SMS (if enabled)
            if self.messaging_enabled:
                new_messages = self._check_sms()
                if new_messages:
                    self._process_new_messages(new_messages)

        except Exception as e:
            logger.error(f"Communication monitoring failed: {e}")

    def _check_email(self) -> List[Dict[str, Any]]:
        """Check for new emails via IMAP."""
        try:
            import imapclient
            import email

            # Email settings from environment
            email_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
            email_user = os.getenv("EMAIL_USERNAME")
            email_pass = os.getenv("EMAIL_PASSWORD")

            if not all([email_user, email_pass]):
                logger.warning("Email credentials not configured")
                return []

            # Connect to IMAP
            server = imapclient.IMAPClient(email_server, ssl=True)
            server.login(email_user, email_pass)

            # Select inbox
            server.select_folder("INBOX")

            # Search for unseen messages
            messages = server.search(["UNSEEN"])

            new_emails = []
            for msgid in messages[:5]:  # Limit to 5 recent
                raw_message = server.fetch([msgid], ["BODY[]", "FLAGS"])
                email_message = email.message_from_bytes(raw_message[msgid][b"BODY[]"])

                # Extract basic info
                subject = email_message.get("Subject", "No Subject")
                from_addr = email_message.get("From", "Unknown")

                # Get body (text/plain preferred)
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(
                                "utf-8", errors="ignore"
                            )
                            break
                else:
                    body = email_message.get_payload(decode=True).decode(
                        "utf-8", errors="ignore"
                    )

                email_data = {
                    "subject": subject,
                    "from": from_addr,
                    "date": email_message.get("Date"),
                    "body": body[:500],  # Limit body length
                    "msgid": msgid,
                }
                new_emails.append(email_data)

            server.logout()
            return new_emails

        except ImportError:
            logger.warning("IMAP libraries not available - email monitoring disabled")
            return []
        except Exception as e:
            logger.error(f"Email check failed: {e}")
            return []

    def _check_sms(self) -> List[Dict[str, Any]]:
        """Check for new SMS messages via Twilio."""
        try:
            from twilio.rest import Client

            # Twilio settings
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            phone_number = os.getenv("TWILIO_PHONE_NUMBER")

            if not all([account_sid, auth_token, phone_number]):
                logger.warning("Twilio credentials not configured")
                return []

            client = Client(account_sid, auth_token)

            # Get recent messages
            messages = client.messages.list(to=phone_number, limit=5)

            new_messages = []
            for message in messages:
                if message.direction == "inbound":
                    sms_data = {
                        "from": message.from_,
                        "body": message.body,
                        "date": message.date_sent.isoformat()
                        if message.date_sent
                        else None,
                        "sid": message.sid,
                    }
                    new_messages.append(sms_data)

            return new_messages

        except ImportError:
            logger.warning("Twilio not available - SMS monitoring disabled")
            return []
        except Exception as e:
            logger.error(f"SMS check failed: {e}")
            return []

    def _process_new_emails(self, emails: List[Dict[str, Any]]):
        """Process new emails and notify user."""
        for email in emails:
            summary = f"New email from {email['from']}: {email['subject'][:50]}..."
            logger.info(f"Processing email: {summary}")

            # Publish notification
            bus.publish(
                "agent.email_notification",
                {"type": "email", "summary": summary, "details": email},
            )

    def _process_new_messages(self, messages: List[Dict[str, Any]]):
        """Process new SMS messages."""
        for message in messages:
            summary = f"New SMS from {message['from']}: {message['body'][:50]}..."
            logger.info(f"Processing SMS: {summary}")

            # Publish notification
            bus.publish(
                "agent.sms_notification",
                {"type": "sms", "summary": summary, "details": message},
            )

    def draft_email(self, recipient: str, subject: str, body: str) -> str:
        """Draft an email with user approval."""
        draft = f"To: {recipient}\nSubject: {subject}\n\n{body}"
        return draft

    def draft_text(self, recipient: str, message: str) -> str:
        """Draft a text message."""
        return f"To: {recipient}\n{message}"
    
    def process(self, query: str, context: Dict[str, Any]) -> str:
        """
        Process assistant queries using the standardized interface.
        
        Args:
            query: User query
            context: Additional context
            
        Returns:
            Processed response
        """
        # Use the existing handle_assistant_query method
        try:
            # Get recent memories to provide context
            recent_memories = self.get_recent_memories(limit=3)
            memory_context = "\n".join(recent_memories) if recent_memories else ""
            
            # Combine with semantic memory context
            semantic_context = self.semantic_memory.get_context_for_llm()
            
            # Create enhanced context
            enhanced_context = {
                **context,
                "memory_context": memory_context,
                "semantic_context": semantic_context,
                "capabilities": self.get_capabilities()
            }
            
            # Get response from LLM
            response = self.llm.get_response(
                query,
                role="assistant",
                context=enhanced_context
            )
            
            # Check if response requires verification
            if self._requires_verification(response):
                if not self.llm.verify_action(f"Assistant action: {response}"):
                    response = "I'm sorry, but I cannot perform that action due to safety verification."
            
            return response
            
        except Exception as e:
            logger.error(f"Assistant processing error: {e}")
            raise ProcessingError(f"Failed to process assistant query: {e}")
    
    def simple_process(self, query: str) -> str:
        """
        Simplified processing for fallback.
        """
        return f"I understand you need help with: {query}. Let me assist you."
    
    def rule_based_response(self, query: str) -> str:
        """
        Rule-based response for fallback.
        """
        query_lower = query.lower()
        
        if "remind" in query_lower:
            return "I can set reminders for you. What would you like me to remind you about?"
        elif "email" in query_lower:
            return "I can help with emails. Who would you like to email and what's the message?"
        elif "search" in query_lower:
            return "I can search for information. What are you looking for?"
        elif "calendar" in query_lower or "schedule" in query_lower:
            return "I can help with scheduling. What would you like to schedule?"
        else:
            return "I can help with that. Let me think about the best way to assist you."
