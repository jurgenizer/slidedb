import os
import sys
import click
from flask_migrate import Migrate
from app import create_app, db
from app.models import User, Role, Permission, Case, Answer

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role,
                Permission=Permission, Case=Case, Answer=Answer)

@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)