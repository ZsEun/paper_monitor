#!/usr/bin/env python3
"""CDK app entry point for the Academic Journal Monitor infrastructure."""
import aws_cdk as cdk
from stacks.journal_monitor_stack import JournalMonitorStack

app = cdk.App()
JournalMonitorStack(app, "AcademicJournalMonitorStack")
app.synth()
