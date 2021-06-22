# Copyright (c) 2018, INRIA
# Copyright (c) 2018, University of Lille
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.

# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.

# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import logging
import time
from multiprocessing import Queue

import pytest

from mock import Mock

from thespian.actors import ActorExitRequest

from powerapi.report import Report
from powerapi.puller import PullerActor
from powerapi.message import StartMessage, ErrorMessage
from powerapi.filter import Filter, RouterWithoutRuleException

from ..actor.abstract_test_actor import AbstractTestActor
from ..db_utils import FakeDB, AbstractTestActorWithDB, define_database_content, REPORT1, REPORT2
from ...utils import DummyActor, is_actor_alive


def define_filter(filt):
    """
    Decorator to set the _filt
    attribute for individual tests.
    """
    def wrap(func):
        setattr(func, '_filter', filt)
        return func
    return wrap


def pytest_generate_tests(metafunc):
    """
    Function called by pytest when collecting a test_XXX function

    define the content fixtures in test environement with collected the
    value _content if it exist or with an empty content

    :param metafunc: the test context given by pytest
    """
    if 'content' in metafunc.fixturenames:
        content = getattr(metafunc.function, '_content', None)
        if isinstance(content, list):
            metafunc.parametrize('content', [content])
        else:
            metafunc.parametrize('content', [[]])


    if 'filt' in metafunc.fixturenames:
        filt = getattr(metafunc.function, '_filter', None)
        metafunc.parametrize('filt', [filt])


def filter_rule(report):
    return True

class TestPuller(AbstractTestActorWithDB):

    @pytest.fixture
    def fake_dispatcher(self, system):
        dispatcher = system.createActor(DummyActor)
        system.tell(dispatcher, 'dispatcher')
        return dispatcher

    @pytest.fixture
    def fake_filter(self, fake_dispatcher):
        fake_filter = Filter()
        fake_filter.filter(filter_rule, fake_dispatcher)
        return fake_filter

    @pytest.fixture
    def empty_filter(self):
        fake_filter = Filter()
        return fake_filter

    @pytest.fixture
    def actor(self, system, fake_db, filt, fake_filter):
        filter = fake_filter if filt is None else filt
        puller = system.createActor(PullerActor)
        yield puller
        system.tell(puller, ActorExitRequest())

    @pytest.fixture
    def actor_config(self, system, actor, fake_db, fake_filter):
        return {'name': 'puller_test', 'database': fake_db, 'report_filter': fake_filter, 'report_model': None, 'stream_mode': False}

    def test_create_puller_with_router_without_rules_must_raise_RouterWithoutRuleException(self, system, empty_filter, fake_db):
        puller = system.createActor(PullerActor)
        puller_config = {'name': 'puller_test', 'database': fake_db, 'report_filter': empty_filter, 'report_model': None, 'stream_mode': False}
        answer = system.ask(puller, StartMessage(puller_config))
        assert isinstance(answer, ErrorMessage)
        assert answer.error_message == 'filter without rules'

    @define_database_content([REPORT1, REPORT2])
    def test_start_actor_with_db_thath_contains_2_report_make_actor_send_reports_to_dispatcher(self, system, started_actor, fake_dispatcher, content):
        for report in content:
            assert system.listen() == ('dispatcher', report)

    def test_starting_actor_in_non_stream_mode_make_it_terminate_itself_after_empty_db(self, system, started_actor):
        time.sleep(1)
        assert not is_actor_alive(system, started_actor)

    def test_starting_actor_in_stream_mode_dont_terminate_itself_after_empty_db(self, system, actor, fake_db, fake_filter):
        assert is_actor_alive(system, actor)
        puller_config = {'name': 'puller_test', 'database': fake_db, 'report_filter': fake_filter, 'report_model': None, 'stream_mode': True}
        answer = system.ask(actor, StartMessage(puller_config))
        time.sleep(1)
        assert is_actor_alive(system, actor)

