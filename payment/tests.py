from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from payment.models import Transaction
from payment.serializers import DepositSerializer, STUDENT_PLAN_AMOUNT, PREMIUM_PLAN_AMOUNT
from django.utils import timezone
import json

User = get_user_model()


class DepositSerializerTestCase(TestCase):
    """Test cases for DepositSerializer validation"""
    
    def setUp(self):
        # Create test users
        self.student_user = User.objects.create_user(
            username='student1',
            email='student@university.edu',
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='regular1',
            email='user@gmail.com',
            password='testpass123'
        )
    
    def test_valid_student_plan_with_student_email(self):
        """Test that student plan (3000) is accepted with student email"""
        data = {
            'amount': STUDENT_PLAN_AMOUNT,
            'email': 'student@university.edu'
        }
        serializer = DepositSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_valid_premium_plan_with_any_email(self):
        """Test that premium plan (7500) is accepted with any email"""
        data = {
            'amount': PREMIUM_PLAN_AMOUNT,
            'email': 'user@gmail.com'
        }
        serializer = DepositSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # Also test with student email
        data['email'] = 'student@university.edu'
        serializer = DepositSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_student_plan_rejected_for_non_student_email(self):
        """Test that student plan (3000) is rejected for non-student emails"""
        data = {
            'amount': STUDENT_PLAN_AMOUNT,
            'email': 'user@gmail.com'
        }
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
    
    def test_invalid_amount_3001(self):
        """Test that amount 3001 is rejected"""
        data = {
            'amount': 3001,
            'email': 'user@gmail.com'
        }
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
    
    def test_invalid_amount_4000(self):
        """Test that amount 4000 is rejected"""
        data = {
            'amount': 4000,
            'email': 'user@gmail.com'
        }
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
    
    def test_invalid_amount_7499(self):
        """Test that amount 7499 is rejected"""
        data = {
            'amount': 7499,
            'email': 'student@university.edu'
        }
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
    
    def test_invalid_amount_negative(self):
        """Test that negative amounts are rejected"""
        data = {
            'amount': -100,
            'email': 'user@gmail.com'
        }
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
    
    def test_invalid_amount_zero(self):
        """Test that zero amount is rejected"""
        data = {
            'amount': 0,
            'email': 'user@gmail.com'
        }
        serializer = DepositSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)


class PaymentWebhookTestCase(TestCase):
    """Test cases for payment webhook handler"""
    
    def setUp(self):
        # Create test users
        self.student_user = User.objects.create_user(
            username='student1',
            email='student@university.edu',
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='regular1',
            email='user@gmail.com',
            password='testpass123'
        )
    
    def test_valid_student_plan_payment(self):
        """Test that valid student plan payment grants student subscription"""
        # Create transaction
        transaction = Transaction.objects.create(
            user=self.student_user,
            amount_paid=3000.0,
            type_of_transaction='Payment',
            reference='test_ref_student',
            completed=False
        )
        
        # Simulate webhook data
        from payment.views import handle_successful_payment
        webhook_data = {'reference': 'test_ref_student'}
        
        response = handle_successful_payment(webhook_data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['plan'], 'student')
        
        # Verify user subscription
        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.user_type, 'student')
        self.assertTrue(self.student_user.premium_user)
        self.assertIsNotNone(self.student_user.subscription_end_date)
        
        # Verify transaction completed
        transaction.refresh_from_db()
        self.assertTrue(transaction.completed)
    
    def test_valid_premium_plan_payment(self):
        """Test that valid premium plan payment grants premium subscription"""
        # Create transaction
        transaction = Transaction.objects.create(
            user=self.regular_user,
            amount_paid=7500.0,
            type_of_transaction='Payment',
            reference='test_ref_premium',
            completed=False
        )
        
        # Simulate webhook data
        from payment.views import handle_successful_payment
        webhook_data = {'reference': 'test_ref_premium'}
        
        response = handle_successful_payment(webhook_data)
        
        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['plan'], 'premium')
        
        # Verify user subscription
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.user_type, 'premium')
        self.assertTrue(self.regular_user.premium_user)
        self.assertIsNotNone(self.regular_user.subscription_end_date)
        
        # Verify transaction completed
        transaction.refresh_from_db()
        self.assertTrue(transaction.completed)
    
    def test_student_plan_rejected_for_non_student_email(self):
        """Test that student plan payment is rejected for non-student emails"""
        # Create transaction with regular user trying to pay student price
        transaction = Transaction.objects.create(
            user=self.regular_user,
            amount_paid=3000.0,
            type_of_transaction='Payment',
            reference='test_ref_invalid_student',
            completed=False
        )
        
        # Simulate webhook data
        from payment.views import handle_successful_payment
        webhook_data = {'reference': 'test_ref_invalid_student'}
        
        response = handle_successful_payment(webhook_data)
        
        # Verify response is rejection
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['status'], 'student_email_required')
        
        # Verify user did NOT get subscription
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.user_type, 'free')
        self.assertFalse(self.regular_user.premium_user)
        
        # Verify transaction marked completed but access denied
        transaction.refresh_from_db()
        self.assertTrue(transaction.completed)
    
    def test_invalid_amount_rejected(self):
        """Test that invalid payment amounts are rejected"""
        invalid_amounts = [3001, 4000, 5000, 6000, 7499, 10000]
        
        for amount in invalid_amounts:
            with self.subTest(amount=amount):
                # Create transaction
                transaction = Transaction.objects.create(
                    user=self.regular_user,
                    amount_paid=amount,
                    type_of_transaction='Payment',
                    reference=f'test_ref_invalid_{amount}',
                    completed=False
                )
                
                # Simulate webhook data
                from payment.views import handle_successful_payment
                webhook_data = {'reference': f'test_ref_invalid_{amount}'}
                
                response = handle_successful_payment(webhook_data)
                
                # Verify response is rejection
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data['status'], 'invalid_amount')
                
                # Verify user did NOT get subscription
                self.regular_user.refresh_from_db()
                self.assertEqual(self.regular_user.user_type, 'free')
                self.assertFalse(self.regular_user.premium_user)
                
                # Verify transaction marked completed but access denied
                transaction.refresh_from_db()
                self.assertTrue(transaction.completed)
