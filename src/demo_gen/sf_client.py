"""Salesforce client for querying opportunities and creating activities"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from simple_salesforce import Salesforce

from demo_gen.config import SalesforceConfig


class SalesforceClient:
    """Client for Salesforce operations"""

    def __init__(self, config: SalesforceConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.sf: Optional[Salesforce] = None

        if not dry_run:
            self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Salesforce using credentials from environment"""
        username = os.getenv("SF_USERNAME")
        password = os.getenv("SF_PASSWORD")
        security_token = os.getenv("SF_SECURITY_TOKEN")

        if not all([username, password, security_token]):
            raise ValueError(
                "Missing Salesforce credentials. Set SF_USERNAME, SF_PASSWORD, "
                "and SF_SECURITY_TOKEN environment variables."
            )

        instance_url = self.config.instance_url.replace("https://", "").rstrip("/")
        domain = self._resolve_login_domain(instance_url)

        self.sf = Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain,
        )

    def _resolve_login_domain(self, instance_url: str) -> str:
        """Resolve login domain from an instance URL"""
        if instance_url.startswith("test.") or instance_url == "test.salesforce.com":
            return "test"
        if instance_url.endswith(".my.salesforce.com"):
            return instance_url.split(".my.salesforce.com")[0]
        return "login"

    def _escape_soql(self, value: str) -> str:
        """Escape a value for SOQL string literals"""
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _format_soql_date(self, value: str) -> str:
        """Format a date string for SOQL"""
        if value.startswith("'") and value.endswith("'"):
            return value
        return f"'{value}'"

    def query_opportunities(self) -> List[Dict[str, Any]]:
        """Query opportunities based on configuration criteria"""
        if self.dry_run:
            return self._mock_opportunities()

        query_config = self.config.query

        where_clauses = []

        # Opportunity type filter
        if query_config.opportunity_type:
            opportunity_type = self._escape_soql(query_config.opportunity_type)
            where_clauses.append(f"Type = '{opportunity_type}'")

        # Stage filter
        if query_config.stages_allowed:
            stages = "', '".join(self._escape_soql(stage) for stage in query_config.stages_allowed)
            where_clauses.append(f"StageName IN ('{stages}')")

        # Exclusion field
        if query_config.exclude_if_omitted_field:
            where_clauses.append(f"{query_config.exclude_if_omitted_field} = false")

        # Close date range
        start_date = self._format_soql_date(query_config.close_date_range.start)
        end_date = self._format_soql_date(query_config.close_date_range.end)
        where_clauses.append(f"CloseDate >= {start_date} AND CloseDate <= {end_date}")

        where_clause = " AND ".join(where_clauses)

        soql = f"""
            SELECT Id, Name, StageName, Amount, CloseDate, AccountId, OwnerId
            FROM Opportunity
            WHERE {where_clause}
            ORDER BY CloseDate ASC
            LIMIT {query_config.limit}
        """

        result = self.sf.query(soql)
        return result["records"]

    def _mock_opportunities(self) -> List[Dict[str, Any]]:
        """Generate mock opportunities for dry-run mode"""
        return [
            {
                "Id": f"006MOCK{i:08d}",
                "Name": f"Demo Opportunity {i}",
                "StageName": "Discovery",
                "Amount": 50000 + (i * 10000),
                "CloseDate": "2025-11-15",
                "AccountId": f"001MOCK{i:08d}",
                "OwnerId": "005MOCK00000001",
            }
            for i in range(10)
        ]

    def create_event(
        self,
        subject: str,
        start_datetime: str,
        duration_minutes: int,
        related_to_id: str,
        owner_id: str,
        description: Optional[str] = None,
        run_id: Optional[str] = None,
        tag_field: Optional[str] = None,
    ) -> str:
        """Create a calendar event (meeting)"""
        if self.dry_run:
            return f"00UMOCK{datetime.utcnow().timestamp()}"

        # Calculate end time
        from datetime import datetime, timedelta

        start_dt = datetime.fromisoformat(start_datetime.replace("Z", "+00:00"))
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_data = {
            "Subject": subject,
            "StartDateTime": start_datetime,
            "EndDateTime": end_dt.isoformat(),
            "WhatId": related_to_id,
            "OwnerId": owner_id,
            "IsAllDayEvent": False,
        }

        if description:
            event_data["Description"] = description
        if run_id and tag_field:
            event_data[tag_field] = run_id

        result = self.sf.Event.create(event_data)
        return result["id"]

    def create_task(
        self,
        subject: str,
        activity_date: str,
        related_to_id: str,
        owner_id: str,
        description: Optional[str] = None,
        task_subtype: str = "Email",
        run_id: Optional[str] = None,
        tag_field: Optional[str] = None,
    ) -> str:
        """Create a task (typically used for email activities)"""
        if self.dry_run:
            return f"00TMOCK{datetime.utcnow().timestamp()}"

        task_data = {
            "Subject": subject,
            "ActivityDate": activity_date,
            "WhatId": related_to_id,
            "OwnerId": owner_id,
            "Status": "Completed",
            "TaskSubtype": task_subtype,
        }

        if description:
            task_data["Description"] = description
        if run_id and tag_field:
            task_data[tag_field] = run_id

        result = self.sf.Task.create(task_data)
        return result["id"]

    def get_contacts_for_account(self, account_id: str) -> List[Dict[str, Any]]:
        """Get contacts associated with an account"""
        if self.dry_run:
            return [
                {
                    "Id": f"003MOCK{i:08d}",
                    "Name": f"Contact {i}",
                    "Email": f"contact{i}@example.com",
                }
                for i in range(3)
            ]

        soql = f"""
            SELECT Id, Name, Email, Title
            FROM Contact
            WHERE AccountId = '{account_id}'
            LIMIT 10
        """

        result = self.sf.query(soql)
        return result["records"]

    def tag_record_with_run_id(
        self, object_name: str, record_id: str, run_id: str, tag_field: str
    ) -> None:
        """Tag a record with the run ID for later cleanup/tracking"""
        if self.dry_run:
            return

        obj = getattr(self.sf, object_name)
        obj.update(record_id, {tag_field: run_id})

    def delete_records_by_run_id(
        self, object_name: str, tag_field: str, run_id: str
    ) -> int:
        """Delete all records tagged with a specific run ID"""
        if self.dry_run:
            return 0

        soql = f"SELECT Id FROM {object_name} WHERE {tag_field} = '{run_id}'"
        result = self.sf.query_all(soql)

        deleted = 0
        obj = getattr(self.sf, object_name)
        for record in result["records"]:
            obj.delete(record["Id"])
            deleted += 1

        return deleted

    def delete_record(self, object_name: str, record_id: str) -> None:
        """Delete a record by ID"""
        if self.dry_run:
            return

        obj = getattr(self.sf, object_name)
        obj.delete(record_id)
