"""Central application context.

Owns shared application state (config + active project) and lazily provides
service instances. Acts as a lightweight dependency-injection container so
future phases can resolve services through a single entry point.

Phase 2: wiring only - services contain no implementation yet.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from core.activity import ActivityService
from core.config import AppConfig
from core.events import EventBus
from core.snapshot_manager import SnapshotManager
from models.project import Project
from models.snapshot import Snapshot
from services.article_service import ArticleService
from services.obx_service import OBXService
from services.mdb_service import MDBService
from services.xocd_export_service import XocdExportService
from services.xocd_svn_service import XocdSvnService
from services.ocd_export_service import OcdExportService
from services.price_update_service import PriceUpdateService
from services.version_update_service import VersionUpdateService
from services.sif_validation_service import SifValidationService  # CET SIF (disconnectable)
from services.obx_validation_service import ObxValidationService
from services.pip_service import PipService
from services.price_list_service import PriceListService
from services.mdb_reconcile_service import MdbReconcileService
from services.mdb_reverse_engineering_service import MdbReverseEngineeringService
from services.maintenance_repository_link_service import MaintenanceRepositoryLinkService
from services.distribution_region_service import DistributionRegionService
from services.option_service import OptionService
from services.option_value_service import OptionValueService
from services.pdm_service import PDMService
from services.product_profile_service import ProductProfileService
from services.project_service import ProjectService
from services.property_service import PropertyService
from services.property_value_service import PropertyValueService
from services.snapshot_service import SnapshotService
from services.validation_service import ValidationService
from services.engineering.engineering_initialization_service import EngineeringInitializationService
from services.engineering.engineering_family_service import EngineeringFamilyService
from services.engineering.engineering_member_service import EngineeringMemberService
from services.engineering.engineering_property_service import EngineeringPropertyService
from services.engineering.engineering_class_service import EngineeringClassService
from services.engineering.engineering_assignment_service import EngineeringAssignmentService
from services.engineering.engineering_reduction_service import EngineeringReductionService
from services.engineering.candidate_strategy_service import CandidateStrategyService
from services.engineering.pdm_family_reduction_service import PDMFamilyReductionService
from services.engineering.engineering_text_service import EngineeringTextService
from services.engineering.engineering_relation_service import EngineeringRelationService
from services.engineering.engineering_artbase_service import EngineeringArtbaseService
from services.engineering.engineering_value_table_service import EngineeringValueTableService
from services.engineering.engineering_relationship_service import EngineeringRelationshipService
from services.engineering.engineering_validation_service import EngineeringValidationService
from services.engineering.material_picking_service import MaterialPickingService
from services.engineering.engineering_generation_service import EngineeringGenerationRule, EngineeringGenerationService
from services.engineering.generation_rules import default_engineering_generation_rules
from services.engineering.engineering_repository import EngineeringRepository

if TYPE_CHECKING:
    from services.base_service import BaseService

TService = TypeVar("TService", bound="BaseService")


class ApplicationContext:
    """Shared services and application state container."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config: AppConfig = config or AppConfig()
        self.project: Project = Project()
        self.snapshot_manager: SnapshotManager = SnapshotManager()
        # Keep PDM Development data and published-repository Maintenance data
        # in separate snapshots so repository imports never overwrite Development.
        self._pdm_snapshot: Snapshot | None = None
        self._repository_snapshot: Snapshot | None = None
        self._snapshot_source: str = "pdm"
        self._product_names: dict[str, str] = {}
        self._event_bus: EventBus | None = None
        self._activity_service: ActivityService | None = None
        self._loading_engine: object | None = None
        self._services: dict[type, object] = {}
        self._engineering_repository: EngineeringRepository | None = None
        self._engineering_generation_rules: tuple[EngineeringGenerationRule, ...] = default_engineering_generation_rules()
        self._engineering_generation_service: EngineeringGenerationService | None = None
        self._service_factories: dict[type, type] = {
            ProjectService: ProjectService,
            SnapshotService: SnapshotService,
            PDMService: PDMService,
            MDBService: MDBService,
            MdbReverseEngineeringService: MdbReverseEngineeringService,
            MaintenanceRepositoryLinkService: MaintenanceRepositoryLinkService,
            ArticleService: ArticleService,
            PropertyService: PropertyService,
            PropertyValueService: PropertyValueService,
            OptionService: OptionService,
            OptionValueService: OptionValueService,
            ProductProfileService: ProductProfileService,
            ValidationService: ValidationService,
            EngineeringInitializationService: EngineeringInitializationService,
            EngineeringFamilyService: EngineeringFamilyService,
            EngineeringMemberService: EngineeringMemberService,
            EngineeringPropertyService: EngineeringPropertyService,
            EngineeringAssignmentService: EngineeringAssignmentService,
            EngineeringReductionService: EngineeringReductionService,
            CandidateStrategyService: CandidateStrategyService,
            PDMFamilyReductionService: PDMFamilyReductionService,
            EngineeringTextService: EngineeringTextService,
            EngineeringRelationService: EngineeringRelationService,
            EngineeringArtbaseService: EngineeringArtbaseService,
            EngineeringValueTableService: EngineeringValueTableService,
            EngineeringRelationshipService: EngineeringRelationshipService,
            EngineeringValidationService: EngineeringValidationService,
            MaterialPickingService: MaterialPickingService,
        }

    def get_service(self, service_type: type[TService]) -> TService:
        if service_type not in self._services:
            factory = self._service_factories.get(service_type, service_type)
            self._services[service_type] = factory(self)
        return self._services[service_type]  # type: ignore[return-value]

    @property
    def active_snapshot(self) -> Snapshot | None:
        return self.snapshot_manager.get_active_snapshot()

    @property
    def snapshot_source(self) -> str:
        return self._snapshot_source

    @property
    def pdm_snapshot(self) -> Snapshot | None:
        return self._pdm_snapshot

    @property
    def repository_snapshot(self) -> Snapshot | None:
        return self._repository_snapshot

    def register_pdm_snapshot(self, snapshot: Snapshot | None) -> None:
        self._pdm_snapshot = snapshot
        if self._snapshot_source == "pdm":
            if snapshot is None:
                self.snapshot_manager.clear_snapshot()
            else:
                self.snapshot_manager.load_snapshot(snapshot)

    def register_repository_snapshot(self, snapshot: Snapshot | None) -> None:
        self._repository_snapshot = snapshot
        if self._snapshot_source == "repository":
            if snapshot is None:
                self.snapshot_manager.clear_snapshot()
            else:
                self.snapshot_manager.load_snapshot(snapshot)

    def activate_snapshot_source(self, source: str) -> None:
        if source not in {"pdm", "repository"}:
            raise ValueError(f"Unknown snapshot source: {source}")
        self._snapshot_source = source
        snapshot = self._pdm_snapshot if source == "pdm" else self._repository_snapshot
        if snapshot is None:
            self.snapshot_manager.clear_snapshot()
        else:
            self.snapshot_manager.load_snapshot(snapshot)

    def clear_active_snapshot(self) -> None:
        if self._snapshot_source == "pdm":
            self._pdm_snapshot = None
        else:
            self._repository_snapshot = None
        self.snapshot_manager.clear_snapshot()

    def set_product_registry(self, products) -> None:
        for product in products:
            pid = getattr(product, "id", None)
            if pid is None:
                continue
            name = getattr(product, "name", "") or ""
            if name or str(pid) not in self._product_names:
                self._product_names[str(pid)] = name

    def product_name(self, product_id) -> str:
        if not product_id:
            return ""
        return self._product_names.get(str(product_id), "")

    def product_type_name(self, product_id) -> str:
        name = self.product_name(product_id)
        return name.split("/")[0].strip() if name else ""

    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            self._event_bus = EventBus()
        return self._event_bus

    @property
    def activity_service(self) -> ActivityService:
        if self._activity_service is None:
            self._activity_service = ActivityService(event_bus=self.event_bus)
        return self._activity_service

    @property
    def loading_engine(self):
        if self._loading_engine is None:
            from services.loading import LoadingEngine
            self._loading_engine = LoadingEngine(self)
        return self._loading_engine

    @property
    def project_service(self) -> ProjectService:
        return self.get_service(ProjectService)

    @property
    def snapshot_service(self) -> SnapshotService:
        return self.get_service(SnapshotService)

    @property
    def pdm_service(self) -> PDMService:
        return self.get_service(PDMService)

    @property
    def mdb_service(self) -> MDBService:
        return self.get_service(MDBService)

    @property
    def mdb_reverse_engineering_service(self) -> MdbReverseEngineeringService:
        return self.get_service(MdbReverseEngineeringService)

    @property
    def maintenance_repository_link_service(self) -> MaintenanceRepositoryLinkService:
        return self.get_service(MaintenanceRepositoryLinkService)

    @property
    def article_service(self) -> ArticleService:
        return self.get_service(ArticleService)

    @property
    def property_service(self) -> PropertyService:
        return self.get_service(PropertyService)

    @property
    def property_value_service(self) -> PropertyValueService:
        return self.get_service(PropertyValueService)

    @property
    def option_service(self) -> OptionService:
        return self.get_service(OptionService)

    @property
    def option_value_service(self) -> OptionValueService:
        return self.get_service(OptionValueService)

    @property
    def product_profile_service(self) -> ProductProfileService:
        return self.get_service(ProductProfileService)

    @property
    def candidate_strategy_service(self) -> CandidateStrategyService:
        """Additional legacy-PDM candidate proposals; never the validator."""
        return self.get_service(CandidateStrategyService)

    @property
    def pdm_family_reduction_service(self) -> PDMFamilyReductionService:
        """Legacy ProductsList boundary validator for reduction candidates."""
        return self.get_service(PDMFamilyReductionService)

    @property
    def engineering_text_service(self) -> EngineeringTextService:
        return self.get_service(EngineeringTextService)

    @property
    def engineering_relation_service(self) -> EngineeringRelationService:
        return self.get_service(EngineeringRelationService)

    @property
    def engineering_artbase_service(self) -> EngineeringArtbaseService:
        return self.get_service(EngineeringArtbaseService)

    @property
    def engineering_value_table_service(self) -> EngineeringValueTableService:
        return self.get_service(EngineeringValueTableService)

    @property
    def validation_service(self) -> ValidationService:
        return self.get_service(ValidationService)

    @property
    def price_list_service(self) -> PriceListService:
        return self.get_service(PriceListService)

    @property
    def mdb_reconcile_service(self) -> MdbReconcileService:
        return self.get_service(MdbReconcileService)

    @property
    def distribution_region_service(self) -> DistributionRegionService:
        return self.get_service(DistributionRegionService)

    @property
    def xocd_export_service(self) -> XocdExportService:
        return self.get_service(XocdExportService)

    @property
    def xocd_svn_service(self) -> XocdSvnService:
        return XocdSvnService()

    @property
    def ocd_export_service(self) -> OcdExportService:
        return self.get_service(OcdExportService)

    @property
    def price_update_service(self) -> PriceUpdateService:
        return self.get_service(PriceUpdateService)

    @property
    def version_update_service(self) -> VersionUpdateService:
        return self.get_service(VersionUpdateService)

    @property
    def sif_validation_service(self) -> SifValidationService:
        return self.get_service(SifValidationService)

    @property
    def obx_validation_service(self) -> ObxValidationService:
        return self.get_service(ObxValidationService)

    @property
    def pip_service(self) -> PipService:
        return self.get_service(PipService)

    @property
    def obx_service(self) -> OBXService:
        return self.get_service(OBXService)

    @property
    def engineering_initialization_service(self) -> EngineeringInitializationService:
        return self.get_service(EngineeringInitializationService)

    @property
    def engineering_family_service(self) -> EngineeringFamilyService:
        return self.get_service(EngineeringFamilyService)

    @property
    def engineering_member_service(self) -> EngineeringMemberService:
        return self.get_service(EngineeringMemberService)

    @property
    def engineering_property_service(self) -> EngineeringPropertyService:
        return self.get_service(EngineeringPropertyService)

    @property
    def engineering_class_service(self) -> EngineeringClassService:
        return self.get_service(EngineeringClassService)

    @property
    def engineering_assignment_service(self) -> EngineeringAssignmentService:
        return self.get_service(EngineeringAssignmentService)

    @property
    def engineering_reduction_service(self) -> EngineeringReductionService:
        return self.get_service(EngineeringReductionService)

    @property
    def engineering_relationship_service(self) -> EngineeringRelationshipService:
        return self.get_service(EngineeringRelationshipService)

    @property
    def engineering_validation_service(self) -> EngineeringValidationService:
        return self.get_service(EngineeringValidationService)

    @property
    def material_picking_service(self) -> MaterialPickingService:
        return self.get_service(MaterialPickingService)

    @property
    def engineering_generation_service(self) -> EngineeringGenerationService:
        if self._engineering_generation_service is None:
            self._engineering_generation_service = EngineeringGenerationService(self, rules=self._engineering_generation_rules)
        return self._engineering_generation_service

    @property
    def engineering_repository(self) -> EngineeringRepository:
        if self._engineering_repository is None:
            self._engineering_repository = EngineeringRepository(self)
        return self._engineering_repository
