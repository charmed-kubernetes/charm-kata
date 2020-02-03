import os
import sys
from unittest.mock import MagicMock

# mock dependencies which we don't care about covering in our tests
ch = MagicMock()
sys.modules['charmhelpers'] = ch
sys.modules['charmhelpers.core'] = ch.core
sys.modules['charmhelpers.core.hookenv'] = ch.core.hookenv
sys.modules['charmhelpers.fetch'] = ch.fetch

charms = MagicMock()
sys.modules['charms'] = charms
sys.modules['charms.reactive'] = charms.reactive

os.environ['JUJU_MODEL_UUID'] = 'test-1234'
