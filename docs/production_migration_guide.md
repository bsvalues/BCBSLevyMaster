# Production Database Migration Guide

This guide provides instructions for managing database migrations in a production environment for the Levy Calculation System.

## Overview

The Levy Calculation System uses Flask-Migrate (which is built on Alembic) to handle database schema migrations. This approach allows for:

1. Version control of database schema changes
2. Safe application of changes to production databases
3. Ability to roll back problematic migrations
4. Tracking of migration history

## Migration Workflow

### Development Environment

1. **Make model changes**: Update your SQLAlchemy models in the `models.py` file
2. **Generate migration script**: `python migrate.py migrate -m "Description of changes"`
3. **Review migration script**: Check the generated migration script in `migrations/versions/`
4. **Apply migration**: `python migrate.py upgrade`
5. **Test the changes**: Verify the application works with the new schema

### Production Environment

1. **Backup the database**: Always create a full backup before applying migrations
   ```bash
   pg_dump -U username -h hostname database_name > backup_$(date +%Y%m%d).sql
   ```

2. **Deploy updated application code**: Ensure your application code with updated models is deployed

3. **Apply migrations**: Run the migration command
   ```bash
   python migrate.py upgrade
   ```

4. **Verify application functionality**: Run tests or manual checks to ensure everything works

5. **Rollback plan**: If issues occur, use the downgrade command
   ```bash
   python migrate.py downgrade
   ```

## Common Commands

- **Initialize migration repository** (first-time setup):
  ```bash
  python migrate.py init
  ```

- **Create a new migration**:
  ```bash
  python migrate.py migrate -m "Description of changes"
  ```

- **Upgrade to the latest version**:
  ```bash
  python migrate.py upgrade
  ```

- **Downgrade one version**:
  ```bash
  python migrate.py downgrade
  ```

- **Show current version**:
  ```bash
  python migrate.py current
  ```

- **Show migration history**:
  ```bash
  python migrate.py history
  ```

## Best Practices

1. **Clear commit messages**: Use descriptive messages when generating migrations
2. **One change per migration**: Keep migrations focused on one schema change
3. **Test migrations thoroughly**: Verify both upgrade and downgrade paths
4. **Always backup production data**: Before applying any migration
5. **Schedule migrations during low-traffic periods**: Minimize disruption
6. **Document schema changes**: Keep track of significant changes

## Handling Data Migrations

For migrations that require data transformations:

1. Use the `op.execute()` function in migration scripts for running custom SQL
2. For complex data migrations, consider creating separate scripts
3. For large tables, consider batching updates to prevent timeouts

Example data migration in a migration script:

```python
def upgrade():
    # Schema changes
    op.add_column('users', sa.Column('full_name', sa.String(255)))
    
    # Data migration
    op.execute("UPDATE users SET full_name = first_name || ' ' || last_name")
    
    # More schema changes
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')
```

## Troubleshooting

### Migration Conflicts

If you encounter migration conflicts (multiple heads):

```bash
python migrate.py merge heads
```

### Failed Migrations

If a migration fails in production:

1. Check the error message
2. Attempt to fix the issue
3. If unsuccessful, downgrade to the previous version
4. Restore from backup if necessary

### Database Locks

If migrations are blocked by locks:

1. Identify blocking connections using PostgreSQL query tools
2. Consider terminating blocking connections (with caution)
3. Run migrations during maintenance windows

## Production Deployment Checklist

- [ ] Review all model changes and ensure they're covered by migrations
- [ ] Run migrations in a staging environment with production-like data
- [ ] Create a full database backup
- [ ] Document the migration plan including rollback procedures
- [ ] Schedule maintenance window if needed
- [ ] Apply migrations to production
- [ ] Verify application functionality
- [ ] Monitor application performance after migration