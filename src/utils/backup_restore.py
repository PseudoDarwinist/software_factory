#!/usr/bin/env python3
"""
Backup and Restore Utilities for Mission Control Data

Provides utilities to:
- Create backups of JSON data before migration
- Create database backups after migration
- Restore from backups if needed
- Verify backup integrity
"""

import json
import os
import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.database import db
from src.app import create_app


class BackupManager:
    """Manages backup and restore operations for Mission Control data"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def create_json_backup(self, data_file: str, artifacts_dir: str) -> str:
        """Create backup of JSON data and artifacts before migration"""
        print("=== Creating JSON Data Backup ===")
        
        backup_name = f"json_backup_{self.timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        try:
            # Backup main data.json file
            data_file_path = Path(data_file)
            if data_file_path.exists():
                shutil.copy2(data_file_path, backup_path / "data.json")
                print(f"✓ Backed up {data_file} to {backup_path / 'data.json'}")
            else:
                print(f"⚠ Data file {data_file} not found")
            
            # Backup artifacts directory
            artifacts_path = Path(artifacts_dir)
            if artifacts_path.exists():
                backup_artifacts_path = backup_path / "artifacts"
                shutil.copytree(artifacts_path, backup_artifacts_path)
                print(f"✓ Backed up {artifacts_dir} to {backup_artifacts_path}")
            else:
                print(f"⚠ Artifacts directory {artifacts_dir} not found")
            
            # Create backup metadata
            metadata = {
                "backup_type": "json",
                "timestamp": self.timestamp,
                "created_at": datetime.now().isoformat(),
                "source_data_file": str(data_file_path.absolute()),
                "source_artifacts_dir": str(artifacts_path.absolute()) if artifacts_path.exists() else None,
                "backup_path": str(backup_path.absolute())
            }
            
            with open(backup_path / "backup_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ JSON backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            print(f"❌ Failed to create JSON backup: {e}")
            raise
    
    def create_database_backup(self, db_path: Optional[str] = None) -> str:
        """Create backup of SQLite database after migration"""
        print("=== Creating Database Backup ===")
        
        backup_name = f"db_backup_{self.timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        try:
            # Get database path from Flask app if not provided
            if not db_path:
                app = create_app()
                with app.app_context():
                    db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            
            db_file_path = Path(db_path)
            if not db_file_path.exists():
                raise FileNotFoundError(f"Database file not found: {db_path}")
            
            # Copy database file
            backup_db_path = backup_path / "mission_control.db"
            shutil.copy2(db_file_path, backup_db_path)
            print(f"✓ Backed up database to {backup_db_path}")
            
            # Create database schema dump
            schema_dump_path = backup_path / "schema.sql"
            self._dump_database_schema(str(db_file_path), str(schema_dump_path))
            print(f"✓ Created schema dump: {schema_dump_path}")
            
            # Create data export
            data_export_path = backup_path / "data_export.json"
            self._export_database_data(str(db_file_path), str(data_export_path))
            print(f"✓ Created data export: {data_export_path}")
            
            # Create backup metadata
            metadata = {
                "backup_type": "database",
                "timestamp": self.timestamp,
                "created_at": datetime.now().isoformat(),
                "source_db_path": str(db_file_path.absolute()),
                "backup_path": str(backup_path.absolute()),
                "files": {
                    "database": "mission_control.db",
                    "schema": "schema.sql",
                    "data_export": "data_export.json"
                }
            }
            
            with open(backup_path / "backup_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Database backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            print(f"❌ Failed to create database backup: {e}")
            raise
    
    def _dump_database_schema(self, db_path: str, output_path: str):
        """Dump database schema to SQL file"""
        conn = sqlite3.connect(db_path)
        try:
            with open(output_path, 'w') as f:
                for line in conn.iterdump():
                    if line.startswith('CREATE TABLE') or line.startswith('CREATE INDEX'):
                        f.write(line + '\n')
        finally:
            conn.close()
    
    def _export_database_data(self, db_path: str, output_path: str):
        """Export database data to JSON file"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            export_data = {}
            
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                export_data[table] = [dict(row) for row in rows]
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
                
        finally:
            conn.close()
    
    def restore_from_json_backup(self, backup_path: str, target_data_file: str, target_artifacts_dir: str):
        """Restore JSON data from backup"""
        print(f"=== Restoring from JSON Backup: {backup_path} ===")
        
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")
        
        try:
            # Restore data.json
            backup_data_file = backup_dir / "data.json"
            if backup_data_file.exists():
                target_path = Path(target_data_file)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_data_file, target_path)
                print(f"✓ Restored data.json to {target_path}")
            
            # Restore artifacts
            backup_artifacts_dir = backup_dir / "artifacts"
            if backup_artifacts_dir.exists():
                target_artifacts_path = Path(target_artifacts_dir)
                if target_artifacts_path.exists():
                    shutil.rmtree(target_artifacts_path)
                shutil.copytree(backup_artifacts_dir, target_artifacts_path)
                print(f"✓ Restored artifacts to {target_artifacts_path}")
            
            print("✅ JSON restore completed successfully")
            
        except Exception as e:
            print(f"❌ Failed to restore from JSON backup: {e}")
            raise
    
    def restore_from_database_backup(self, backup_path: str, target_db_path: Optional[str] = None):
        """Restore database from backup"""
        print(f"=== Restoring from Database Backup: {backup_path} ===")
        
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")
        
        try:
            # Get target database path
            if not target_db_path:
                app = create_app()
                with app.app_context():
                    target_db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            
            backup_db_file = backup_dir / "mission_control.db"
            if not backup_db_file.exists():
                raise FileNotFoundError(f"Backup database file not found: {backup_db_file}")
            
            # Create backup of current database if it exists
            target_path = Path(target_db_path)
            if target_path.exists():
                current_backup = target_path.with_suffix(f".backup_{self.timestamp}")
                shutil.copy2(target_path, current_backup)
                print(f"✓ Created backup of current database: {current_backup}")
            
            # Restore database
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_db_file, target_path)
            print(f"✓ Restored database to {target_path}")
            
            print("✅ Database restore completed successfully")
            
        except Exception as e:
            print(f"❌ Failed to restore from database backup: {e}")
            raise
    
    def verify_backup_integrity(self, backup_path: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        print(f"=== Verifying Backup Integrity: {backup_path} ===")
        
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            return {"valid": False, "error": f"Backup directory not found: {backup_path}"}
        
        results = {
            "valid": True,
            "backup_path": backup_path,
            "files_found": [],
            "files_missing": [],
            "errors": []
        }
        
        try:
            # Check metadata file
            metadata_file = backup_dir / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                results["metadata"] = metadata
                results["files_found"].append("backup_metadata.json")
                
                backup_type = metadata.get("backup_type")
                
                if backup_type == "json":
                    # Verify JSON backup files
                    expected_files = ["data.json"]
                    for file_name in expected_files:
                        file_path = backup_dir / file_name
                        if file_path.exists():
                            results["files_found"].append(file_name)
                        else:
                            results["files_missing"].append(file_name)
                    
                    # Check artifacts directory
                    artifacts_dir = backup_dir / "artifacts"
                    if artifacts_dir.exists():
                        results["files_found"].append("artifacts/")
                    
                elif backup_type == "database":
                    # Verify database backup files
                    expected_files = ["mission_control.db", "schema.sql", "data_export.json"]
                    for file_name in expected_files:
                        file_path = backup_dir / file_name
                        if file_path.exists():
                            results["files_found"].append(file_name)
                        else:
                            results["files_missing"].append(file_name)
                
            else:
                results["files_missing"].append("backup_metadata.json")
                results["errors"].append("Metadata file not found")
            
            # Verify JSON files are valid
            for json_file in ["data.json", "data_export.json", "backup_metadata.json"]:
                json_path = backup_dir / json_file
                if json_path.exists():
                    try:
                        with open(json_path, 'r') as f:
                            json.load(f)
                    except json.JSONDecodeError as e:
                        results["errors"].append(f"Invalid JSON in {json_file}: {e}")
            
            # Check if backup is valid
            if results["files_missing"] or results["errors"]:
                results["valid"] = False
            
            # Print results
            print(f"Files found: {len(results['files_found'])}")
            for file_name in results["files_found"]:
                print(f"  ✓ {file_name}")
            
            if results["files_missing"]:
                print(f"Files missing: {len(results['files_missing'])}")
                for file_name in results["files_missing"]:
                    print(f"  ✗ {file_name}")
            
            if results["errors"]:
                print(f"Errors: {len(results['errors'])}")
                for error in results["errors"]:
                    print(f"  ✗ {error}")
            
            if results["valid"]:
                print("✅ Backup integrity verification passed")
            else:
                print("❌ Backup integrity verification failed")
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Verification failed: {e}")
            print(f"❌ Backup verification error: {e}")
        
        return results
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        print("=== Available Backups ===")
        
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "backup_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        backup_info = {
                            "name": backup_dir.name,
                            "path": str(backup_dir),
                            "type": metadata.get("backup_type", "unknown"),
                            "timestamp": metadata.get("timestamp"),
                            "created_at": metadata.get("created_at"),
                            "size": self._get_directory_size(backup_dir)
                        }
                        backups.append(backup_info)
                        
                    except Exception as e:
                        print(f"⚠ Failed to read metadata for {backup_dir.name}: {e}")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        if not backups:
            print("No backups found")
        else:
            for backup in backups:
                print(f"  {backup['name']} ({backup['type']}) - {backup['created_at']} - {backup['size']}")
        
        return backups
    
    def _get_directory_size(self, directory: Path) -> str:
        """Get human-readable directory size"""
        total_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024.0:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024.0
        return f"{total_size:.1f} TB"


def main():
    """Main backup/restore function"""
    if len(sys.argv) < 2:
        print("Usage: python backup_restore.py <command> [options]")
        print("Commands:")
        print("  backup-json <data_file> <artifacts_dir>  - Create JSON backup")
        print("  backup-db [db_path]                      - Create database backup")
        print("  restore-json <backup_path> <data_file> <artifacts_dir>  - Restore from JSON backup")
        print("  restore-db <backup_path> [db_path]       - Restore from database backup")
        print("  verify <backup_path>                     - Verify backup integrity")
        print("  list                                     - List available backups")
        sys.exit(1)
    
    command = sys.argv[1]
    backup_manager = BackupManager()
    
    try:
        if command == "backup-json":
            if len(sys.argv) < 4:
                print("Error: data_file and artifacts_dir required")
                sys.exit(1)
            data_file = sys.argv[2]
            artifacts_dir = sys.argv[3]
            backup_path = backup_manager.create_json_backup(data_file, artifacts_dir)
            print(f"Backup created: {backup_path}")
        
        elif command == "backup-db":
            db_path = sys.argv[2] if len(sys.argv) > 2 else None
            backup_path = backup_manager.create_database_backup(db_path)
            print(f"Backup created: {backup_path}")
        
        elif command == "restore-json":
            if len(sys.argv) < 5:
                print("Error: backup_path, data_file, and artifacts_dir required")
                sys.exit(1)
            backup_path = sys.argv[2]
            data_file = sys.argv[3]
            artifacts_dir = sys.argv[4]
            backup_manager.restore_from_json_backup(backup_path, data_file, artifacts_dir)
        
        elif command == "restore-db":
            if len(sys.argv) < 3:
                print("Error: backup_path required")
                sys.exit(1)
            backup_path = sys.argv[2]
            db_path = sys.argv[3] if len(sys.argv) > 3 else None
            backup_manager.restore_from_database_backup(backup_path, db_path)
        
        elif command == "verify":
            if len(sys.argv) < 3:
                print("Error: backup_path required")
                sys.exit(1)
            backup_path = sys.argv[2]
            results = backup_manager.verify_backup_integrity(backup_path)
            sys.exit(0 if results["valid"] else 1)
        
        elif command == "list":
            backup_manager.list_backups()
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        print(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()