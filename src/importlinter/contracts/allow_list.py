from importlinter import Contract, ContractCheck, fields, output
from importlinter.application import contract_utils
from importlinter.domain import helpers as importlinter_helpers
import grimp


class AllowListContract(Contract):
    """
    Allow-list contracts check that one set of modules are only imported by another set of modules.
    Configuration options:
        - target_modules:    A set of Modules that are adressed by this contract.
        - allowed_importers: A set of Modules that is allowed to import the targeted modules.

        - ignore_imports:    A set of ImportExpressions. These imports will be ignored if the import
                            would cause a contract to be broken, adding it to the set will cause
                            the contract be kept instead. (Optional.) This can be used to signal
                            illegitimate imports that need to be removed in the long terms.
        - unmatched_ignore_imports_alerting: Decides how to report when the expression in the
                            `ignore_imports` set is not found in the graph. Valid values are
                            "none", "warn", "error". Default value is "error".
    """

    target_modules = fields.ListField(subfield=fields.ModuleExpressionField())
    allowed_importers = fields.ListField(subfield=fields.ModuleExpressionField())

    ignore_imports = fields.SetField(subfield=fields.ImportExpressionField(), required=False)
    unmatched_ignore_imports_alerting = fields.EnumField(
        contract_utils.AlertLevel, default=contract_utils.AlertLevel.ERROR
    )

    as_packages = fields.BooleanField(required=False, default=True)

    def check(self, graph: grimp.ImportGraph, verbose: bool) -> ContractCheck:
        warnings = contract_utils.remove_ignored_imports(
            graph=graph,
            ignore_imports=self.ignore_imports,
            unmatched_alerting=self.unmatched_ignore_imports_alerting,
        )

        target_modules = {
            module.name
            for module in importlinter_helpers.module_expressions_to_modules(
                graph, self.target_modules
            )
        }
        if self.as_packages:
            children = set()
            for target_module in target_modules:
                children.update(graph.find_descendants(target_module))
            target_modules.update(children)

        allowed_modules = {
            module.name
            for module in importlinter_helpers.module_expressions_to_modules(
                graph, self.allowed_importers
            )
        }
        if self.as_packages:
            children = set()
            for target_module in allowed_modules:
                children.update(graph.find_descendants(target_module))
            allowed_modules.update(children)

        # Target modules can import between themselves
        allowed_modules.update(target_modules)

        illegal_imports = []
        for target_module in target_modules:
            for importing_module in graph.find_modules_that_directly_import(target_module):
                if importing_module not in allowed_modules:
                    illegal_imports.append(
                        *graph.get_import_details(
                            importer=importing_module, imported=target_module
                        )
                    )

        return ContractCheck(
            kept=len(illegal_imports) == 0,
            warnings=warnings,
            metadata={"illegal_imports": illegal_imports},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        illegal_imports = check.metadata["illegal_imports"]

        output.print_error(
            "Following imports do not respect the allow-list policy:",
            bold=False,
        )

        for illegal_import in illegal_imports:
            importer, imported, line_number = (
                illegal_import["importer"],
                illegal_import["imported"],
                illegal_import["line_number"],
            )
            output.print_error(f"{importer} -> {imported} (l.{line_number})")