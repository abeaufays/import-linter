import grimp
import pytest
from grimp.adaptors import graph as grimp_graphs
from importlinter.application.app_config import settings
from importlinter.contracts import allow_list as allow_list_contract
from adapters.printing import FakePrinter


class TestAllowListContract:
    @staticmethod
    def _build_default_graph() -> grimp.ImportGraph:
        graph = grimp_graphs.ImportGraph()
        for module in (
            "octoenergy",
            "octoenergy.domain",
            "octoenergy.domain.debt",
            "octoenergy.domain.debt.delinquent_debt.queries",
            "octoenergy.domain.debt.queries",
            "octoenergy.domain.debt.operations",
            "octoenergy.domain.payments",
            "octoenergy.domain.payments.queries",
            "octoenergy.domain.payments.operations",
            "octoenergy.data.debt",
            "octoenergy.data.debt.models",
            "octoenergy.data.debt.other_models",
            "octoenergy.data.payments",
            "octoenergy.data.payments.models",
        ):
            graph.add_module(module)
        return graph

    @pytest.mark.parametrize(
        "import_details,contract_kept,description",
        [
            (
                {
                    "importer": "octoenergy.domain.debt.queries",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Queries in debt domain can import debt models",
            ),
            (
                {
                    "importer": "octoenergy.data.debt.other_models",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Other debt models can import targeted debt models",
            ),
            (
                {
                    "importer": "octoenergy.domain.payment.operations",
                    "imported": "octoenergy.data.payments.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Unrelated payments queries can import unrelated payments models",
            ),
            (
                {
                    "importer": "octoenergy.domain.debt",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                False,
                "Root of domain debt cannot import targeted debt models, it's not included by wildcard expression",
            ),
            (
                {
                    "importer": "octoenergy.domain.payment.operations",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                False,
                "Payments queries are not allowed to import debt models",
            ),
            (
                {
                    "importer": "octoenergy.data.payments.models",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                False,
                "Payments models are not allowed to import debt models",
            ),
            (
                {
                    "importer": "octoenergy.domain.debt.delinquent_debt.queries",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Deeper debt module are allowed to import debt models",
            ),
        ],
    )
    def test_detects_illegal_imports_correctly_without_as_package(
        self, import_details, contract_kept, description
    ):
        # Tested contract says that the module octoenergy.data.debt.models can be imported
        # only from octoenergy.data.debt children and octoenergy.domain.debt children

        graph = self._build_default_graph()
        graph.add_import(**import_details)

        contract = allow_list_contract.AllowListContract(
            name="Allow list contract",
            session_options={
                "contract_types": ["allow_list: tools.importlinter.AllowListContract"],
                "root_packages": ["octoenergy"],
            },
            contract_options={
                "target_modules": ("octoenergy.data.debt.models"),
                "allowed_importers": ("octoenergy.data.debt.**", "octoenergy.domain.debt.**"),
                "as_packages": "False",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept == contract_kept, description

    @pytest.mark.parametrize(
        "import_details,contract_kept,description",
        [
            (
                {
                    "importer": "octoenergy.data.debt.other_models",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Modules inside target package can import each others",
            ),
            (
                {
                    "importer": "octoenergy.data.payments.models",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                False,
                "Payments models are not allowed to import debt models",
            ),
            (
                {
                    "importer": "octoenergy.domain.payments.queries",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                False,
                "Payments queries are not allowed to import debt queries",
            ),
            (
                {
                    "importer": "octoenergy.domain.payment.operations",
                    "imported": "octoenergy.data.payments.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Unrelated payments operations are allowed to import unrelated payments models",
            ),
            (
                {
                    "importer": "octoenergy.domain.debt",
                    "imported": "octoenergy.data.debt",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Root debt domain is allowed to import root of data debt",
            ),
            (
                {
                    "importer": "octoenergy.domain.debt.delinquent_debt.queries",
                    "imported": "octoenergy.data.debt.models",
                    "line_number": 7,
                    "line_contents": "print",
                },
                True,
                "Deeper debt modules are allowed to import debt models",
            ),
        ],
    )
    def test_detects_illegal_imports_correctly_with_as_package(
        self, import_details, contract_kept, description
    ):
        # Tested contracts says the package octoenergy.data.debt can only be imported
        # from octoenergy.domain.debt
        graph = self._build_default_graph()
        graph.add_import(**import_details)

        contract = allow_list_contract.AllowListContract(
            name="Allow list contract",
            session_options={
                "contract_types": ["allow_list: tools.importlinter.AllowListContract"],
                "root_packages": ["octoenergy"],
            },
            contract_options={
                "target_modules": ("octoenergy.data.debt"),
                "allowed_importers": ("octoenergy.domain.debt"),
                "as_packages": "True",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept == contract_kept, description

    def test_detects_illegal_imports_if_target_uses_wildcards_but_not_as_packages(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="octoenergy.domain.payment.operations",
            imported="octoenergy.data.debt.models",
            line_number=1,
            line_contents="print",
        )
        contract = allow_list_contract.AllowListContract(
            name="Allow list contract",
            session_options={
                # "contract_types": ["allow_list: tools.importlinter.AllowListContract"],
                "root_packages": ["octoenergy"],
            },
            contract_options={
                "target_modules": ("octoenergy.data.debt.**"),
                "allowed_importers": ("octoenergy.data.debt.**", "octoenergy.domain.debt.**"),
                "as_packages": "False",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert not contract_check.kept

    def test_render_broken_contract(self):
        settings.configure(PRINTER=FakePrinter())
        graph = self._build_default_graph()
        graph.add_import(
            importer="octoenergy.domain.payments.queries",
            imported="octoenergy.data.debt.models",
            line_number=7,
            line_contents="print",
        )
        contract = allow_list_contract.AllowListContract(
            name="Allow list contract",
            session_options={
                "contract_types": ["private_imports: tools.importlinter.AllowListContract"],
                "root_packages": ["octoenergy"],
            },
            contract_options={
                "target_modules": ("octoenergy.data.debt.models"),
                "allowed_importers": ("octoenergy.data.debt", "octoenergy.domain.debt"),
                "as_packages": "true",
            },
        )
        contract_check = contract.check(graph=graph, verbose=False)
        contract.render_broken_contract(contract_check)
        # breakpoint()
        settings.PRINTER.pop_and_assert(
            """
            Following imports do not respect the allow-list policy:
            octoenergy.domain.payments.queries -> octoenergy.data.debt.models (l.7)
"""

        )