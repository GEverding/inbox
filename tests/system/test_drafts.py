# -*- coding: utf-8 -*-
import pytest
import time
from inbox.client.errors import NotFoundError
from base import for_all_available_providers, timeout_loop
from conftest import TEST_MAX_DURATION_SECS, TEST_GRANULARITY_CHECK_SECS


@timeout_loop('file')
def wait_for_file(client, file_id):
    try:
        file_obj = client.namespaces[0].files.find(file_id)
        return True
    except NotFoundError:
        return False


@timeout_loop('draft')
def wait_for_draft(client, draft_id):
    try:
        draft = client.namespaces[0].drafts.find(draft_id)
        print "FOUND"
        return True
    except NotFoundError:
        return False


@timeout_loop('draft_removed')
def check_draft_is_removed(client, draft_id):
    try:
        draft = client.namespaces[0].drafts.find(draft_id)
        return False
    except NotFoundError:
        return True


@for_all_available_providers
def test_draft(client):
    # Let's create a draft, attach a file to it and delete it

    # Create the file
    myfile = client.namespaces[0].files.create()
    myfile.filename = 'file_%d.txt' % time.time()
    myfile.data = 'This is a file'
    myfile.save()
    wait_for_file(client, myfile.id)

    # And the draft
    mydraft = client.namespaces[0].drafts.create()
    mydraft.to = [{'email': client.namespaces[0]['email_address']}]
    mydraft.subject = "Test draft from Inbox - %s" % time.strftime("%H:%M:%S")
    mydraft.body = "This is a test email, disregard this."
    mydraft.attach(myfile)
    mydraft.save()
    wait_for_draft(client, mydraft.id)
    mydraft.send()

    start_time = time.time()
    found_draft = False
    # Not sure about the correct behaviour for this one -
    # are sent drafts kept?
    # check_draft_is_removed(client, mydraft.id)


if __name__ == '__main__':
    pytest.main([__file__])
