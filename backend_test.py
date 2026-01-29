#!/usr/bin/env python3
"""
Backend API Testing for Lead Processing Service MVP
Tests all API endpoints and AI classifier functionality
"""

import requests
import sys
import json
from datetime import datetime
import asyncio
import os
from pathlib import Path

# Add backend to path for imports
sys.path.append('/app/backend')

class LeadProcessingAPITester:
    def __init__(self, base_url="https://teleleads.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def test_root_endpoint(self):
        """Test GET /api/ endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                success = "message" in data and "running" in data["message"].lower()
                details = f"Response: {data}" if success else f"Unexpected response: {data}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("Root endpoint (/api/)", success, details)
            return success
        except Exception as e:
            self.log_test("Root endpoint (/api/)", False, str(e))
            return False

    def test_stats_endpoint(self):
        """Test GET /api/stats endpoint"""
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                required_fields = ["total", "by_type", "high_urgency", "new_leads"]
                success = all(field in data for field in required_fields)
                
                if success and "by_type" in data:
                    by_type_fields = ["hot", "warm", "cold"]
                    success = all(field in data["by_type"] for field in by_type_fields)
                
                details = f"Stats: {data}" if success else f"Missing fields in: {data}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("Stats endpoint (/api/stats)", success, details)
            return success, data if success else {}
        except Exception as e:
            self.log_test("Stats endpoint (/api/stats)", False, str(e))
            return False, {}

    def test_leads_endpoint(self):
        """Test GET /api/leads endpoint"""
        try:
            response = requests.get(f"{self.api_url}/leads", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                success = isinstance(data, list)
                details = f"Retrieved {len(data)} leads" if success else f"Expected list, got: {type(data)}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("Leads endpoint (/api/leads)", success, details)
            return success, data if success else []
        except Exception as e:
            self.log_test("Leads endpoint (/api/leads)", False, str(e))
            return False, []

    def test_leads_filtering(self):
        """Test leads endpoint with filters"""
        filters = [
            ("status", "new"),
            ("lead_type", "hot"),
            ("urgency", "high")
        ]
        
        all_success = True
        for filter_name, filter_value in filters:
            try:
                response = requests.get(
                    f"{self.api_url}/leads",
                    params={filter_name: filter_value},
                    timeout=10
                )
                success = response.status_code == 200
                
                if success:
                    data = response.json()
                    success = isinstance(data, list)
                    details = f"Filter {filter_name}={filter_value}: {len(data)} results"
                else:
                    details = f"Status: {response.status_code}"
                
                self.log_test(f"Leads filtering ({filter_name}={filter_value})", success, details)
                if not success:
                    all_success = False
                    
            except Exception as e:
                self.log_test(f"Leads filtering ({filter_name}={filter_value})", False, str(e))
                all_success = False
        
        return all_success

    def test_telegram_webhook(self):
        """Test POST /api/telegram/webhook endpoint with mock data"""
        mock_webhook_data = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "text": "Привет! Мне нужна помощь с настройкой сайта. Срочно нужно до завтра!",
                "chat": {"id": 123456789},
                "from": {
                    "id": 123456789,
                    "username": "test_user",
                    "first_name": "Тестовый"
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/telegram/webhook",
                json=mock_webhook_data,
                timeout=30  # AI processing might take time
            )
            success = response.status_code == 200
            
            if success:
                data = response.json()
                expected_fields = ["status", "reply_sent", "lead_saved"]
                success = all(field in data for field in expected_fields)
                details = f"Response: {data}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("Telegram webhook with AI classification", success, details)
            return success, data if success else {}
        except Exception as e:
            self.log_test("Telegram webhook with AI classification", False, str(e))
            return False, {}

    def test_ai_classifier_direct(self):
        """Test AI classifier directly with mock data"""
        try:
            # Import and test AI classifier
            from ai_classifier import classify_lead
            
            test_messages = [
                "Привет! Мне нужна помощь с настройкой сайта. Срочно нужно до завтра!",
                "Сколько стоит создание интернет-магазина?",
                "Спасибо за информацию!",
                "Хочу заказать разработку мобильного приложения прямо сейчас"
            ]
            
            all_success = True
            for i, message in enumerate(test_messages):
                try:
                    # Run async function
                    result = asyncio.run(classify_lead(message, f"test_session_{i}"))
                    
                    required_fields = ["lead", "lead_type", "service", "urgency", "reply"]
                    success = all(field in result for field in required_fields)
                    
                    if success:
                        # Validate field values
                        success = (
                            isinstance(result["lead"], bool) and
                            result["lead_type"] in ["hot", "warm", "cold"] and
                            result["urgency"] in ["high", "medium", "low"] and
                            isinstance(result["reply"], str) and len(result["reply"]) > 0
                        )
                    
                    details = f"Message: '{message[:30]}...' -> {result}"
                    self.log_test(f"AI Classifier test {i+1}", success, details)
                    
                    if not success:
                        all_success = False
                        
                except Exception as e:
                    self.log_test(f"AI Classifier test {i+1}", False, str(e))
                    all_success = False
            
            return all_success
            
        except Exception as e:
            self.log_test("AI Classifier import/setup", False, str(e))
            return False

    def test_notification_system(self):
        """Test notification system handles missing tokens gracefully"""
        try:
            from telegram_bot import send_notification_to_manager, process_message
            
            # Test with missing tokens (should not crash)
            result1 = asyncio.run(send_notification_to_manager(
                lead_type="hot",
                service="Тестовая услуга",
                urgency="high",
                client_name="Тест",
                client_username="@test",
                message="Тестовое сообщение",
                chat_id=123456
            ))
            
            result2 = asyncio.run(process_message(123456, "Тестовый ответ"))
            
            # Should return False but not crash
            success = result1 is False and result2 is False
            details = "Functions handled missing tokens gracefully"
            
            self.log_test("Notification system (missing tokens)", success, details)
            return success
            
        except Exception as e:
            self.log_test("Notification system (missing tokens)", False, str(e))
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Lead Processing Service Backend Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test basic endpoints
        self.test_root_endpoint()
        stats_success, stats_data = self.test_stats_endpoint()
        leads_success, leads_data = self.test_leads_endpoint()
        
        # Test filtering
        self.test_leads_filtering()
        
        # Test AI integration
        webhook_success, webhook_data = self.test_telegram_webhook()
        ai_success = self.test_ai_classifier_direct()
        
        # Test notification system
        notification_success = self.test_notification_system()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if stats_success and stats_data:
            print(f"📈 Current Stats: {stats_data}")
        
        if leads_success and leads_data:
            print(f"📋 Current Leads: {len(leads_data)} in database")
        
        # Check critical issues
        critical_issues = []
        if not self.test_root_endpoint():
            critical_issues.append("Root endpoint not accessible")
        if not stats_success:
            critical_issues.append("Stats endpoint failing")
        if not leads_success:
            critical_issues.append("Leads endpoint failing")
        if not ai_success:
            critical_issues.append("AI classifier not working")
        
        if critical_issues:
            print(f"\n🚨 Critical Issues Found:")
            for issue in critical_issues:
                print(f"   - {issue}")
        
        return self.tests_passed == self.tests_run, self.test_results

def main():
    tester = LeadProcessingAPITester()
    success, results = tester.run_all_tests()
    
    # Save results
    results_file = "/app/backend_test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "success_rate": f"{(tester.tests_passed/tester.tests_run)*100:.1f}%",
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())