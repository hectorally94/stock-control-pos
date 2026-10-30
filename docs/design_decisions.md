# Stock Control & POS - Database Design Decisions

## Overview

This document explains key architectural decisions in the database schema, particularly regarding tables without foreign key relationships.

---

## Why `daily_summaries` Has No Foreign Key Relationships

### Design Pattern: Aggregation/Summary Table

The `daily_summaries` table is intentionally **unlinked** from other tables because it follows the **Materialized View** pattern, commonly used in data warehousing and OLAP (Online Analytical Processing).

### Technical Justification

#### 1. **Performance Optimization**
- **Problem**: Generating daily reports by joining `sales`, `expenses`, `credit_payments`, and `sale_items` tables with thousands of records is computationally expensive.
- **Solution**: Pre-calculate and store aggregated data once per day.
- **Benefit**: Dashboard loads in milliseconds instead of seconds.

```sql
-- WITHOUT daily_summaries (slow - joins 4+ tables)
SELECT 
    DATE(s.created_at) as date,
    SUM(s.total_amount) as total_sales,
    SUM(e.amount) as total_expenses,
    SUM(CASE WHEN s.payment_method='cash' THEN s.total_amount ELSE 0 END) as cash
FROM sales s
LEFT JOIN expenses e ON DATE(e.expense_date) = DATE(s.created_at)
WHERE s.created_at >= '2025-01-01'
GROUP BY DATE(s.created_at);

-- WITH daily_summaries (fast - single table lookup)
SELECT * FROM daily_summaries 
WHERE summary_date >= '2025-01-01'
ORDER BY summary_date DESC;
```

#### 2. **Data Integrity**
- **Why no FKs?**: The table stores **aggregated snapshots**, not transactional references.
- **Example**: If a sale is deleted (refund), the historical summary for that day remains unchanged (audit requirement).
- **Business Rule**: "Yesterday's revenue was X" is a **fact** that shouldn't change even if transactions are modified today.

#### 3. **Denormalization Strategy**
This is a deliberate **denormalization** for reporting:
- **Normalized tables** (sales, expenses) → Transactional integrity
- **Denormalized table** (daily_summaries) → Fast reporting

#### 4. **Multi-Source Aggregation**
The table consolidates data from **multiple sources**:
```
daily_summaries.total_sales        ← SUM(sales.total_amount)
daily_summaries.total_expenses     ← SUM(expenses.amount)
daily_summaries.credit_collected   ← SUM(credit_payments.amount)
daily_summaries.total_cost_of_goods← SUM(sale_items.quantity * sale_items.purchase_price)
daily_summaries.number_of_customers← COUNT(DISTINCT sales.customer_id)
```
**Question**: Which table should it have a FK to? All of them? None makes more sense.

#### 5. **Update Pattern**
Updated via **scheduled job** (cron/celery):
```python
# Django management command (runs daily at midnight)
def populate_daily_summary(date):
    summary, created = DailySummary.objects.get_or_create(summary_date=date)
    summary.total_sales = Sale.objects.filter(created_at__date=date).aggregate(Sum('total_amount'))['total_amount__sum']
    summary.total_expenses = Expense.objects.filter(expense_date=date).aggregate(Sum('amount'))['amount__sum']
    # ... more aggregations
    summary.save()
```

### Database Design Principles Applied

| Principle | Application |
|-----------|-------------|
| **Separation of Concerns** | Transactional data (sales) vs. analytical data (summaries) |
| **CAP Theorem Trade-off** | Prioritize Availability (fast reads) over strong Consistency (eventual consistency is acceptable) |
| **CQRS Pattern** | Command (write to sales) vs. Query (read from summaries) models are separate |

### Industry Precedents
- **Google Analytics**: Pre-aggregates data in summary tables
- **Stripe Dashboard**: Uses summary tables for revenue reporting
- **Amazon RDS**: Recommends summary tables for reporting dashboards
- **Data Warehousing**: Star schema fact tables (e.g., Snowflake, BigQuery)

---

## Why `store_settings` Has No Foreign Key Relationships

### Design Pattern: Configuration/Settings Table

The `store_settings` table uses the **Key-Value Store** pattern for application configuration.

### Technical Justification

#### 1. **Application-Level Configuration**
- **Purpose**: Stores **global settings** that apply to the entire application, not specific records.
- **Examples**:
  ```
  store_name          = "Ma Boutique"
  currency_code       = "XOF"
  default_tax_rate    = "18.00"
  receipt_footer      = "Merci pour votre achat!"
  low_stock_alert     = "true"
  ```
- **Question**: What would a FK reference? There's no "parent" entity.

#### 2. **Singleton Pattern**
- **Cardinality**: One configuration for the entire store (not per-user, not per-sale).
- **Access Pattern**: `settings = StoreSetting.objects.all()` → Used globally across the app.
- **No Relationships Needed**: Settings don't "belong to" any entity.

#### 3. **Flexible Schema**
- **Dynamic Keys**: Can add new settings without altering database schema.
  ```python
  # Add new setting without migration
  StoreSetting.objects.create(key='enable_loyalty_program', value='true')
  ```
- **Type Agnostic**: Values stored as TEXT, parsed by application layer.

#### 4. **Typical Usage in Django**
```python
# Application reads settings (no joins needed)
def get_setting(key, default=None):
    try:
        return StoreSetting.objects.get(key=key).value
    except StoreSetting.DoesNotExist:
        return default

# Example usage
currency = get_setting('currency_symbol', 'FCFA')
tax_rate = Decimal(get_setting('default_tax_rate', '0'))
```

#### 5. **Alternative Considered: Django's Built-in Settings**
| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Django settings.py** | Fast (loaded at startup) | Requires deployment to change | ❌ Not flexible |
| **Environment variables** | Secure for secrets | Hard to manage many settings | ❌ Not user-friendly |
| **Database table** | Admin can change via UI | Slightly slower | ✅ **Chosen** |

### Database Design Principles Applied

| Principle | Application |
|-----------|-------------|
| **EAV Pattern** | Entity-Attribute-Value model for flexible configuration |
| **Single Source of Truth** | All app settings in one place |
| **Loose Coupling** | Settings table independent of business logic tables |

### Industry Precedents
- **WordPress**: `wp_options` table (key-value, no FKs)
- **Magento**: `core_config_data` table
- **Laravel**: `settings` table in many packages
- **Shopify**: App settings stored in key-value format

---

## Summary: When to Use Standalone Tables

### ✅ **Valid Reasons for No Foreign Keys**

1. **Aggregation Tables** (`daily_summaries`)
   - Data from multiple sources
   - Historical snapshots
   - Performance-critical reads

2. **Configuration Tables** (`store_settings`)
   - Global application settings
   - Singleton pattern
   - No parent entity

3. **Log Tables** (e.g., `audit_logs` for large systems)
   - Write-only performance
   - Retention policies

4. **Queue/Job Tables** (e.g., `celery_tasks`)
   - Transient data
   - External system integration

### ❌ **When FKs Are Required**

- **Transactional tables** (`sales`, `sale_items`)
- **Entity relationships** (`products` → `categories`)
- **Referential integrity needed** (prevent orphaned records)

---

## Validation: Schema Review Checklist

| Table | Has FKs? | Why? | Valid? |
|-------|----------|------|--------|
| `users` | No (root entity) | User is a primary entity | ✅ |
| `action_logs` | Yes → users | Audit trail per user | ✅ |
| `sales` | Yes → users, customers | Transactional relationship | ✅ |
| `daily_summaries` | **No** | Aggregated reporting data | ✅ |
| `store_settings` | **No** | Global configuration | ✅ |

---

## Conclusion

The **absence of foreign keys** in `daily_summaries` and `store_settings` is a **deliberate architectural decision**, not an oversight. Both tables serve specialized purposes that don't fit the traditional relational model:

- **`daily_summaries`**: Optimized for **read-heavy analytics** using pre-aggregated data.
- **`store_settings`**: Implements **flexible configuration** using the key-value pattern.

These patterns are **industry-standard practices** validated by major platforms (Stripe, WordPress, Google Analytics) and align with software engineering principles (CQRS, separation of concerns, performance optimization).

### Further Reading

- [Martin Fowler - Reporting Database](https://martinfowler.com/bliki/ReportingDatabase.html)
- [Database Design for Analytics](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/)
- [Django Best Practices: Settings Management](https://docs.djangoproject.com/en/stable/topics/settings/)
- [Designing Data-Intensive Applications](https://dataintensive.net/) by Martin Kleppmann (Chapter 3: Storage and Retrieval)
