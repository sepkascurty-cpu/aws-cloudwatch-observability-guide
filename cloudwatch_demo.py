#!/usr/bin/env python3
"""AWS CloudWatch observability demo — metrics, logs, alarms.

Usage:
    python cloudwatch_demo.py --demo        # offline simulation, no AWS needed
    python cloudwatch_demo.py --live --region ap-southeast-1
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone

NAMESPACE = "MyApp/Checkout"


# ---------------------------------------------------------------------------
# Offline simulation (no AWS needed)
# ---------------------------------------------------------------------------

def simulate_traffic(minutes=10, seed=42):
    """Generate one synthetic minute of checkout traffic per row.

    Returns a list of dicts: {minute, requests, errors, latency_p99_ms}.
    A slow database shows up as latency climbing while requests stay flat.
    """
    rng = random.Random(seed)
    rows = []
    for minute in range(minutes):
        requests = rng.randint(800, 1200)
        # Error rate is normally ~0.4%; it jumps after minute 6 (bad deploy).
        error_rate = 0.004 if minute < 6 else 0.035
        errors = round(requests * error_rate * rng.uniform(0.8, 1.2))
        latency = rng.uniform(120, 220) if minute < 6 else rng.uniform(900, 1400)
        rows.append({
            "minute": minute,
            "requests": requests,
            "errors": errors,
            "latency_p99_ms": round(latency),
        })
    return rows


def evaluate_alarm(rows, error_rate_threshold=0.01, latency_threshold_ms=500):
    """Replicate a CloudWatch composite alarm: error rate OR latency p99.

    Returns (fired, reasons). An alarm fires when a threshold is breached
    for 2 consecutive evaluation periods (datapoints), like a real alarm
    with DatapointsToAlarm=2.
    """
    reasons = []
    error_breaches = 0
    latency_breaches = 0
    error_reported = False
    latency_reported = False
    for row in rows:
        rate = row["errors"] / row["requests"]
        if rate > error_rate_threshold:
            error_breaches += 1
        else:
            error_breaches = 0
        if row["latency_p99_ms"] > latency_threshold_ms:
            latency_breaches += 1
        else:
            latency_breaches = 0
        if error_breaches >= 2 and not error_reported:
            error_reported = True
            reasons.append(f"error rate {rate:.1%} > {error_rate_threshold:.0%} "
                           f"(minute {row['minute']})")
        if latency_breaches >= 2 and not latency_reported:
            latency_reported = True
            reasons.append(f"latency p99 {row['latency_p99_ms']}ms "
                           f"> {latency_threshold_ms}ms (minute {row['minute']})")
    return bool(reasons), reasons


def run_demo():
    rows = simulate_traffic()
    print("minute | requests | errors | error rate | latency p99")
    print("-------+----------+--------+------------+------------")
    for row in rows:
        rate = row["errors"] / row["requests"]
        print(f"{row['minute']:>6} | {row['requests']:>8} | {row['errors']:>6} | "
              f"{rate:>9.1%} | {row['latency_p99_ms']:>8} ms")
    fired, reasons = evaluate_alarm(rows)
    print()
    if fired:
        print("ALARM: Checkout-Health composite alarm FIRED")
        for reason in reasons:
            print(f"  - {reason}")
        print("  -> SNS would page the on-call; EventBridge routes the "
              "alarm state to a Lambda that rolls back the deploy.")
    else:
        print("OK: no alarm — all metrics within thresholds.")
    return 0 if fired else 0


# ---------------------------------------------------------------------------
# Live mode (needs boto3 + credentials with CloudWatch permissions)
# ---------------------------------------------------------------------------

def put_custom_metric(cw, value, unit="Count"):
    cw.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[{
            "MetricName": "OrdersPlaced",
            "Dimensions": [{"Name": "Environment", "Value": "prod"}],
            "Value": value,
            "Unit": unit,
            "Timestamp": datetime.now(timezone.utc),
        }],
    )
    print(f"Put metric OrdersPlaced={value} into {NAMESPACE}")


def create_alarm(cw, topic_arn):
    """Alarm on error RATE (metric math), not raw error count."""
    cw.put_metric_alarm(
        AlarmName="Checkout-ErrorRate-High",
        AlarmDescription="Page on-call when checkout error rate exceeds 1% for 5 minutes",
        Metrics=[
            {"Id": "errors", "MetricStat": {
                "Metric": {"Namespace": NAMESPACE, "MetricName": "CheckoutErrors",
                           "Dimensions": [{"Name": "Environment", "Value": "prod"}]},
                "Period": 60, "Stat": "Sum"}, "ReturnData": False},
            {"Id": "requests", "MetricStat": {
                "Metric": {"Namespace": NAMESPACE, "MetricName": "CheckoutRequests",
                           "Dimensions": [{"Name": "Environment", "Value": "prod"}]},
                "Period": 60, "Stat": "Sum"}, "ReturnData": False},
            {"Id": "error_rate",
             "Expression": "errors / requests * 100",
             "Label": "Checkout error rate (%)", "ReturnData": True},
        ],
        EvaluationPeriods=5,
        DatapointsToAlarm=3,
        Threshold=1.0,
        ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="notBreaching",
        AlarmActions=[topic_arn],
    )
    print("Created alarm Checkout-ErrorRate-High (error rate > 1%, 3 of 5 datapoints)")


def run_live(region):
    import boto3  # imported lazily so --demo works without it

    cw = boto3.client("cloudwatch", region_name=region)
    put_custom_metric(cw, 1)
    topic = input("SNS topic ARN for alarm actions (leave empty to skip alarm): ").strip()
    if topic:
        create_alarm(cw, topic)
    print("Live run complete. Check the CloudWatch console for the metric.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="CloudWatch observability demo")
    parser.add_argument("--demo", action="store_true", help="offline simulation")
    parser.add_argument("--live", action="store_true", help="run against real AWS")
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()

    if args.live:
        return run_live(args.region)
    return run_demo()


if __name__ == "__main__":
    sys.exit(main())
