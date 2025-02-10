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
import threading
import time

import grpc
from holoscan.conditions import BooleanCondition

from holohub.grpc_operators import holoscan_pb2, holoscan_pb2_grpc


class EntityClientService:
    def __init__(
        self,
        server_address,
        interrupt,
        request_queue,
        response_queue,
        source_operator,
        holoviz_operator,
    ):
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Initializing Entity Client Service - address: {server_address}")
        self.server_address = server_address
        self.interrupt = interrupt
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.source_operator = source_operator
        self.holoviz_operator = holoviz_operator
        self.streaming_thread = None
        self.streaming_status_thread = None

    def start_entity_stream(self):
        try:
            self.logger.info("grpc: Starting streaming client")

            self.channel = grpc.insecure_channel("localhost:50051")
            self.stub = holoscan_pb2_grpc.EntityStub(self.channel)
            self.streaming_thread = threading.Thread(target=self.start_entity_stream_internal)
            self.streaming_thread.start()
            self.streaming_status_thread = threading.Thread(target=self.streaming_status_check)
            self.streaming_status_thread.start()
        except Exception as e:
            self.logger.error(f"grpc: Failed to connect to server at {self.server_address}: {e}")

    def start_entity_stream_internal(self):
        responses = self.stub.EntityStream(self.request_queue.iterator())
        for response in responses:
            self.logger.debug("grpc: adding response to queue")
            self.response_queue.push(response)
            if response.end_of_stream:
                self.logger.debug("grpc: end of stream received")
                break

    def streaming_status_check(self):
        while True:
            if self._streaming_completed():
                self.logger.debug("grpc: sending end_of_stream request")
                self.request_queue.push(holoscan_pb2.EntityRequest(end_of_stream=True))
                break
            time.sleep(0.05)

    def _streaming_completed(self):
        boolean_scheduling_term = next(
            (
                condition
                for _, condition in self.source_operator.conditions.items()
                if type(condition) is BooleanCondition
            ),
            None,
        )

        return (
            not boolean_scheduling_term.check_tick_enabled() if boolean_scheduling_term else False
        )

    def stop_entity_stream(self):
        try:
            self.streaming_thread.join()
            self.logger.info("grpc: Stopping streaming client")
            self.channel.close()
        except Exception as e:
            self.logger.error(f"grpc: Failed to close gRPC channel {e}")
