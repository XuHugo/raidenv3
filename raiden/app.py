import structlog

from raiden.api.rest import APIServer
from raiden.constants import BLOCK_ID_LATEST, RoutingMode
from raiden.exceptions import InvalidSettleTimeout
from raiden.message_handler import MessageHandler
from raiden.network.proxies.proxy_manager import ProxyManager
from raiden.network.rpc.client import JSONRPCClient
from raiden.network.transport.matrix.transport import MatrixTransport
from raiden.raiden_event_handler import EventHandler
from raiden.raiden_service import RaidenService
from raiden.settings import RaidenConfig
from raiden.ui.startup import RaidenBundle, ServicesBundle
from raiden.utils.formatting import to_checksum_address
from raiden.utils.typing import BlockNumber, Optional

log = structlog.get_logger(__name__)


class App:  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        config: RaidenConfig,
        rpc_client: JSONRPCClient,
        proxy_manager: ProxyManager,
        query_start_block: BlockNumber,
        raiden_bundle: RaidenBundle,
        services_bundle: Optional[ServicesBundle],
        transport: MatrixTransport,
        raiden_event_handler: EventHandler,
        message_handler: MessageHandler,
        routing_mode: RoutingMode,
        api_server: APIServer = None,
    ):
        raiden = RaidenService(
            rpc_client=rpc_client,
            proxy_manager=proxy_manager,
            query_start_block=query_start_block,
            raiden_bundle=raiden_bundle,
            services_bundle=services_bundle,
            transport=transport,
            raiden_event_handler=raiden_event_handler,
            message_handler=message_handler,
            routing_mode=routing_mode,
            config=config,
            api_server=api_server,
        )

        # check that the settlement timeout fits the limits of the contract
        settlement_timeout_min = raiden_bundle.token_network_registry.settlement_timeout_min(
            BLOCK_ID_LATEST
        )
        settlement_timeout_max = raiden_bundle.token_network_registry.settlement_timeout_max(
            BLOCK_ID_LATEST
        )
        invalid_settle_timeout = (
            config.settle_timeout < settlement_timeout_min
            or config.settle_timeout > settlement_timeout_max
            or config.settle_timeout < config.reveal_timeout * 2
        )
        if invalid_settle_timeout:
            raise InvalidSettleTimeout(
                (
                    "Settlement timeout for Registry contract {} must "
                    "be in range [{}, {}], is {}"
                ).format(
                    to_checksum_address(raiden_bundle.token_network_registry.address),
                    settlement_timeout_min,
                    settlement_timeout_max,
                    config.settle_timeout,
                )
            )

        self.config = config
        self.raiden = raiden

    def __repr__(self) -> str:
        return "<{} {}>".format(self.__class__.__name__, to_checksum_address(self.raiden.address))

    def start(self) -> None:
        """ Start the raiden app. """
        if self.raiden.stop_event.is_set():
            self.raiden.start()
            log.info("Raiden started", node=to_checksum_address(self.raiden.address))

    def stop(self) -> None:
        """ Stop the raiden app. """
        if not self.raiden.stop_event.is_set():
            self.raiden.stop()
            log.info("Raiden stopped", node=to_checksum_address(self.raiden.address))
