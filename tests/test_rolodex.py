import pytest

from .util.base import config
from .util.contacts import contacts_provider
# Need to set up test config before we can import from
# inbox.server.models.tables.
config()
from inbox.server.models.tables import Contact
from inbox.server.rolodex import merge, poll, MergeError

ACCOUNT_ID = 1


def test_merge(config):
    """Test the basic logic of the merge() function."""
    base = Contact(name='Original Name',
                   email_address='originaladdress@inboxapp.com')
    remote = Contact(name='New Name',
                     email_address='originaladdress@inboxapp.com')
    dest = Contact(name='Original Name',
                   email_address='newaddress@inboxapp.com')
    merge(base, remote, dest)
    assert dest.name == 'New Name'
    assert dest.email_address == 'newaddress@inboxapp.com'


def test_merge_conflict(config):
    """Test that merge() raises an error on conflict."""
    base = Contact(name='Original Name',
                   email_address='originaladdress@inboxapp.com')
    remote = Contact(name='New Name',
                     email_address='originaladdress@inboxapp.com')
    dest = Contact(name='Some Other Name',
                   email_address='newaddress@inboxapp.com')
    with pytest.raises(MergeError):
        merge(base, remote, dest)

    # Check no update in case of conflict
    assert dest.name == 'Some Other Name'
    assert dest.email_address == 'newaddress@inboxapp.com'


def test_add_contacts(contacts_provider, db):
    """Test that added contacts get stored."""
    contacts_provider.supply_contact('Contact One', 'contact.one@email.address')
    contacts_provider.supply_contact('Contact Two', 'contact.two@email.address')

    poll(ACCOUNT_ID, contacts_provider)
    local_contacts = db.session.query(Contact). \
        filter_by(imapaccount_id=ACCOUNT_ID).filter_by(source='local').count()
    remote_contacts = db.session.query(Contact). \
        filter_by(imapaccount_id=ACCOUNT_ID).filter_by(source='remote').count()
    assert local_contacts == 2
    assert remote_contacts == 2


def test_update_contact(contacts_provider, db):
    """Test that subsequent contact updates get stored."""
    contacts_provider.supply_contact('Old Name', 'old@email.address')
    poll(ACCOUNT_ID, contacts_provider)
    result = db.session.query(Contact).filter_by(source='remote').one()

    db.new_session()
    assert result.email_address == 'old@email.address'
    contacts_provider.__init__()
    contacts_provider.supply_contact('New Name', 'new@email.address')
    poll(ACCOUNT_ID, contacts_provider)
    result = db.session.query(Contact).filter_by(source='remote').one()
    assert result.name == 'New Name'
    assert result.email_address == 'new@email.address'


def test_uses_local_updates(contacts_provider, db):
    """Test that non-conflicting local and remote updates to the same contact
    both get stored."""
    contacts_provider.supply_contact('Old Name', 'old@email.address')
    poll(ACCOUNT_ID, contacts_provider)
    result = db.session.query(Contact).filter_by(source='local').one()
    # Fake a local contact update.
    result.name = 'New Name'
    db.session.commit()

    db.new_session()
    contacts_provider.__init__()
    contacts_provider.supply_contact('Old Name', 'new@email.address')
    poll(ACCOUNT_ID, contacts_provider)

    db.new_session()
    remote_result = db.session.query(Contact).filter_by(source='remote').one()
    assert remote_result.name == 'New Name'
    assert remote_result.email_address == 'new@email.address'
    local_result = db.session.query(Contact).filter_by(source='local').one()
    assert local_result.name == 'New Name'
    assert local_result.email_address == 'new@email.address'
