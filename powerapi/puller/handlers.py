# Copyright (C) 2018  University of Lille
# Copyright (C) 2018  INRIA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from powerapi.handler import Handler, StartHandler
from powerapi.database import DBError
from powerapi.message import ErrorMessage, OKMessage, StartMessage


class NoReportExtractedException(Exception):
    """
    Exception raised when the handler can't extract a report from the given
    database
    """


class PullerStartHandler(StartHandler):
    """
    Initialize the database interface
    """

    def __init__(self, next_behaviour):
        """
        :param func next_behaviour: Define the next behaviour to apply after
                                    StartMessage is received.
        """

        #: (func): Define the next behaviour to apply after the StartMessage is
        #: received.
        self.next_behaviour = next_behaviour

    def initialization(self, state):
        """
        Initialize the database and connect all dispatcher to the
        socket_interface

        :param State state: State of the actor.
        :rtype powerapi.State: the new state of the actor
        """
        try:
            state.database.load()
        except DBError as error:
            state.socket_interface.send_control(ErrorMessage(error.msg))
            state.alive = False
            return state

        # Connect to all dispatcher
        for _, dispatcher in state.report_filter.filters:
            dispatcher.connect_data(state.socket_interface.context)

        state.behaviour = self.next_behaviour
        return state