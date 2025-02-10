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
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2_grpc

import holohub.grpc_operators.holoscan_pb2_grpc
from operators.grpc_operators.python.server.application_factory import ApplicationFactory
from operators.grpc_operators.python.server.entity_servicer import HoloscanEntityServicer


class GrpcService:
    def __new__(cls):
        """
        Create a singleton instance of the GrpcService class
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(GrpcService, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.server = None
        self.service = None
        self.logger = logging.getLogger(__name__)

    def initialize(self, port, application_factory: ApplicationFactory):
        self.server_address = f"0.0.0.0:{port}"
        self.application_factory = application_factory

    def start(self, enable_health_check_service=True):
        # if enable_health_check_service:
        #   grpc.health.v1.health_pb2_grpc.add_HealthServicer_to_server(
        #     grpc.health.v1.health.HealthServicer(), self.server
        #   )

        self.service = HoloscanEntityServicer(
            self._create_application_instance, self._destroy_application_instance
        )
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        holohub.grpc_operators.holoscan_pb2_grpc.add_EntityServicer_to_server(
            self.service, self.server
        )
        health_pb2_grpc.add_HealthServicer_to_server(health.HealthServicer(), self.server)

        self.server.add_insecure_port(self.server_address)
        self.server.start()
        self.logger.info(f"grpc: Server listening on {self.server_address}")
        self.server.wait_for_termination()

    def stop(self):
        self.logger.info("grpc: Server shutting down")
        self.server.stop(0)

    def _create_application_instance(
        self, service_name, incoming_request_queue, outgoing_response_queue
    ):
        return self.application_factory.create_new_application_instance(
            service_name, incoming_request_queue, outgoing_response_queue
        )

    def _destroy_application_instance(self, application_instance):
        self.application_factory.destroy_application_instance(application_instance)
