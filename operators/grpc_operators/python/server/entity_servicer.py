# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import queue
import threading
import time

from holohub.grpc_operators import holoscan_pb2 as holoscan_proto
from holohub.grpc_operators.holoscan_pb2_grpc import EntityServicer
from operators.grpc_operators.python.server.application_factory import ApplicationFactory


class HoloscanEntityServicer(EntityServicer):
    def __init__(self, new_entity_stream_rpc, entity_stream_rpc_complete):
        self.new_entity_stream_rpc = new_entity_stream_rpc
        self.entity_stream_rpc_complete = entity_stream_rpc_complete
        self.logger = logging.getLogger(__name__)
        self.last_received_frame_no = -1
        self.outgoing_frames = 0

    def EntityStream(self, request_iterator, context):
        incoming_request_queue = queue.Queue()
        outgoing_response_queue = queue.Queue()
        app = self.new_entity_stream_rpc(
            "EndoscopyToolTracking", incoming_request_queue, outgoing_response_queue
        )

        if app is None:
            raise RuntimeError("Failed to create application instance")

        time.sleep(1)

        thread = threading.Thread(target=self._process_requests, args=(app, request_iterator))
        thread.start()

        while True:
            if app.is_response_available():
                response = app.dequeue_response()
                yield response
                self.logger.debug(
                    f"grpc: outgoing_frame {self.outgoing_frames} - last received frame {self.last_received_frame_no}"
                )
                self.outgoing_frames += 1
                if response.end_of_stream:
                    break

        thread.join()
        application_factory = ApplicationFactory()
        application_factory.destroy_application_instance(app)
        self.logger.info("grpc: EntityStream - RPC completed")

    def _process_requests(self, app, request_iterator):
        try:
            for request in request_iterator:
                if request.end_of_stream:
                    self.logger.debug("grpc: EntityStream - end of stream received")
                    app.enqueue_response(holoscan_proto.EntityResponse(end_of_stream=True))
                    break
                else:
                    self.logger.debug("grpc: EntityStream - new request received")
                    self.last_received_frame_no = request.frame_no
                    app.enqueue_request(request)
        except Exception as ex:
            self.logger.error(f"grpc: EntityStream - exception occurred: {ex}")
            application_factory = ApplicationFactory()
            application_factory.destroy_application_instance(app)
