"""
Test script for Batch 4: PDF Receipt and Excel Export functionality
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_control.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from apps.pos.models import Sale
from apps.pos.utils.receipt_generator import generate_receipt_pdf
from apps.reports.utils.excel_generator import (
    sales_report, inventory_report, expense_report, customer_report
)

def test_pdf_receipt():
    """Test PDF receipt generation"""
    print("\n" + "="*60)
    print("TEST 1: PDF Receipt Generation")
    print("="*60)
    
    # Get a recent sale
    sale = Sale.objects.filter(status='completed').first()
    
    if not sale:
        print("❌ No completed sales found. Skipping PDF test.")
        return False
    
    print(f"✓ Testing with sale: {sale.sale_number}")
    
    try:
        # Generate A4 receipt
        pdf_buffer = generate_receipt_pdf(sale, format='A4')
        pdf_size = len(pdf_buffer.getvalue())
        print(f"✓ A4 receipt generated successfully ({pdf_size} bytes)")
        
        # Generate thermal receipt
        pdf_buffer_thermal = generate_receipt_pdf(sale, format='thermal')
        thermal_size = len(pdf_buffer_thermal.getvalue())
        print(f"✓ Thermal receipt generated successfully ({thermal_size} bytes)")
        
        # Save to file for manual inspection
        with open('test_receipt_a4.pdf', 'wb') as f:
            f.write(pdf_buffer.getvalue())
        print(f"✓ A4 receipt saved to test_receipt_a4.pdf")
        
        with open('test_receipt_thermal.pdf', 'wb') as f:
            f.write(pdf_buffer_thermal.getvalue())
        print(f"✓ Thermal receipt saved to test_receipt_thermal.pdf")
        
        print("\n✅ PDF Receipt Generation: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ PDF Receipt Generation: FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_sales_report():
    """Test Excel sales report generation"""
    print("\n" + "="*60)
    print("TEST 2: Excel Sales Report Generation")
    print("="*60)
    
    try:
        # Generate report for last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        print(f"✓ Generating report from {start_date} to {end_date}")
        
        workbook = sales_report(start_date, end_date)
        
        # Check sheets
        sheet_names = workbook.sheetnames
        print(f"✓ Workbook created with sheets: {', '.join(sheet_names)}")
        
        # Save to file
        workbook.save('test_sales_report.xlsx')
        print(f"✓ Sales report saved to test_sales_report.xlsx")
        
        print("\n✅ Excel Sales Report: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Excel Sales Report: FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_inventory_report():
    """Test Excel inventory report generation"""
    print("\n" + "="*60)
    print("TEST 3: Excel Inventory Report Generation")
    print("="*60)
    
    try:
        workbook = inventory_report()
        
        sheet_names = workbook.sheetnames
        print(f"✓ Workbook created with sheets: {', '.join(sheet_names)}")
        
        # Save to file
        workbook.save('test_inventory_report.xlsx')
        print(f"✓ Inventory report saved to test_inventory_report.xlsx")
        
        print("\n✅ Excel Inventory Report: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Excel Inventory Report: FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_expense_report():
    """Test Excel expense report generation"""
    print("\n" + "="*60)
    print("TEST 4: Excel Expense Report Generation")
    print("="*60)
    
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        print(f"✓ Generating report from {start_date} to {end_date}")
        
        workbook = expense_report(start_date, end_date)
        
        sheet_names = workbook.sheetnames
        print(f"✓ Workbook created with sheets: {', '.join(sheet_names)}")
        
        # Save to file
        workbook.save('test_expense_report.xlsx')
        print(f"✓ Expense report saved to test_expense_report.xlsx")
        
        print("\n✅ Excel Expense Report: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Excel Expense Report: FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_customer_report():
    """Test Excel customer report generation"""
    print("\n" + "="*60)
    print("TEST 5: Excel Customer Report Generation")
    print("="*60)
    
    try:
        workbook = customer_report()
        
        sheet_names = workbook.sheetnames
        print(f"✓ Workbook created with sheets: {', '.join(sheet_names)}")
        
        # Save to file
        workbook.save('test_customer_report.xlsx')
        print(f"✓ Customer report saved to test_customer_report.xlsx")
        
        print("\n✅ Excel Customer Report: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Excel Customer Report: FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BATCH 4 TESTING: PDF Receipts & Excel Exports")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("PDF Receipt Generation", test_pdf_receipt()))
    results.append(("Excel Sales Report", test_excel_sales_report()))
    results.append(("Excel Inventory Report", test_excel_inventory_report()))
    results.append(("Excel Expense Report", test_excel_expense_report()))
    results.append(("Excel Customer Report", test_excel_customer_report()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Batch 4 is complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

