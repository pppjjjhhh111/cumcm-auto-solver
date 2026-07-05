from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.code_generator import CodeGeneratorAgent
from src.agents.code_repair_agent import CodeRepairAgent
from src.agents.figure_planner_agent import FigurePlannerAgent
from src.agents.formula_agent import FormulaAgent
from src.agents.model_selector import ModelSelectorAgent
from src.agents.paper_writer import PaperWriterAgent
from src.agents.problem_parser import ProblemParserAgent
from src.agents.reflection_agent import ReflectionAgent
from src.agents.result_analyzer import ResultAnalyzerAgent
from src.agents.revision_agent import RevisionAgent
from src.agents.solution_competition_agent import SolutionCompetitionAgent
from src.agents.strategy_generator import StrategyGeneratorAgent
from src.agents.task_decomposer import TaskDecomposerAgent
from src.agents.validation import ValidationAgent
from src.core.llm_client import LLMClient, MockLLMClient
from src.core.state import SolverState
from src.rag.retriever import Retriever
from src.tools.data_profiler import DataProfiler
from src.tools.file_loader import FileLoader
from src.tools.python_executor import PythonExecutor
from src.tools.report_exporter import ReportExporter
from src.utils.json_utils import write_json
from src.utils.path_utils import ensure_output_tree


class WorkflowRunner:
    """End-to-end CUMCM auto-solver workflow."""

    def __init__(
        self,
        project_root: Path,
        llm_client: LLMClient | None = None,
        output_dir: Path | None = None,
        max_repairs: int = 3,
        use_rag: bool = False,
        kb_dir: Path | None = None,
        enable_reflection: bool = True,
        export_docx: bool = False,
        export_pdf: bool = False,
    ) -> None:
        self.project_root = project_root.resolve()
        self.llm_client = llm_client or MockLLMClient()
        self.output_dir = (output_dir or self.project_root / "outputs").resolve()
        self.max_repairs = max_repairs
        self.use_rag = use_rag
        self.kb_dir = (kb_dir or self.project_root / "knowledge_base").resolve()
        self.enable_reflection = enable_reflection
        self.export_docx = export_docx
        self.export_pdf = export_pdf
        self.output_dirs = ensure_output_tree(self.output_dir)
        self.log_counter = 0
        if hasattr(self.llm_client, "set_log_path"):
            self.llm_client.set_log_path(self.output_dirs["logs_dir"] / "llm_calls.jsonl")

    def run(self, problem_path: Path, data_path: Path | None = None) -> SolverState:
        problem_path = self._resolve_input(problem_path)
        data_path = self._resolve_input(data_path) if data_path is not None else None
        dirs = ensure_output_tree(self.output_dir)
        state = SolverState(
            project_root=self.project_root,
            problem_path=problem_path,
            data_path=data_path,
            output_dir=dirs["output_dir"],
            code_dir=dirs["code_dir"],
            figures_dir=dirs["figures_dir"],
            logs_dir=dirs["logs_dir"],
            reports_dir=dirs["reports_dir"],
            max_repair_attempts=self.max_repairs,
        )

        loader = FileLoader()
        state.raw_problem = loader.load_problem(problem_path)
        state.raw_data = loader.load_data(data_path)
        self._log("file_loader", {"raw_problem": state.raw_problem, "raw_data": state.raw_data})

        parser = ProblemParserAgent(self.llm_client, state.logs_dir)
        state.parsed_problem = parser.run(state.raw_problem, state.raw_data)
        self._log(parser.name, state.parsed_problem)

        decomposer = TaskDecomposerAgent(self.llm_client, state.logs_dir)
        state.decomposed_tasks = decomposer.run(state.parsed_problem)
        self._log(decomposer.name, state.decomposed_tasks)

        profiler = DataProfiler(figures_dir=state.figures_dir, logs_dir=state.logs_dir)
        state.data_profile = profiler.run(data_path)
        self._log("DataProfiler", state.data_profile)

        state.rag_retrievals = self._retrieve_rag(state) if self.use_rag else []
        if state.rag_retrievals:
            self._log("RAGRetriever", {"results": state.rag_retrievals})

        strategy_generator = StrategyGeneratorAgent(self.llm_client, state.logs_dir)
        state.candidate_strategies = strategy_generator.run(
            state.decomposed_tasks,
            data_profile=state.data_profile,
            retrieved_references=state.rag_retrievals,
        )
        self._log(strategy_generator.name, state.candidate_strategies)

        model_selector = ModelSelectorAgent(self.llm_client, state.logs_dir)
        state.selected_model = model_selector.run(state.candidate_strategies)
        self._log(model_selector.name, state.selected_model)

        solution_competition_agent = SolutionCompetitionAgent(self.llm_client, state.logs_dir)
        state.solution_competition = solution_competition_agent.run(
            state.decomposed_tasks,
            state.candidate_strategies,
            state.data_profile,
        )
        self._log(solution_competition_agent.name, state.solution_competition)
        state.selected_model = self._apply_solution_competition(state.selected_model, state.solution_competition)

        formula_agent = FormulaAgent(self.llm_client, state.logs_dir)
        state.formulas = formula_agent.run(
            selected_strategy=state.selected_model,
            sub_tasks=state.decomposed_tasks,
            model_zoo_entries=[],
            parsed_problem=state.parsed_problem,
        )
        self._log(formula_agent.name, state.formulas)

        figure_planner = FigurePlannerAgent(self.llm_client, state.logs_dir)
        state.figure_plan = figure_planner.run(
            state.parsed_problem,
            state.data_profile,
            state.selected_model,
            execution_results={},
        )
        self._log(figure_planner.name, state.figure_plan)

        code_generator = CodeGeneratorAgent(self.llm_client, state.logs_dir)
        state.generated_code = code_generator.run(
            self.project_root,
            data_path,
            state.figures_dir,
            state.selected_model,
            figure_plan=state.figure_plan,
            data_profile=state.data_profile,
        )
        self._log(code_generator.name, {k: v for k, v in state.generated_code.items() if k != "code"})

        self._execute_with_repair_loop(state)

        state.figure_plan = figure_planner.run(
            state.parsed_problem,
            state.data_profile,
            state.selected_model,
            execution_results=state.execution_result,
        )
        self._log(f"{figure_planner.name}_post_execution", state.figure_plan)

        result_analyzer = ResultAnalyzerAgent(self.llm_client, state.logs_dir)
        state.result_analysis = result_analyzer.run(state.code_dir, state.execution_result)
        self._log(result_analyzer.name, state.result_analysis)

        validation_agent = ValidationAgent(self.llm_client, state.logs_dir)
        state.validation = validation_agent.run(state.result_analysis, state.selected_model)
        self._log(validation_agent.name, state.validation)

        paper_writer = PaperWriterAgent(self.llm_client, state.logs_dir)
        state.paper = paper_writer.run(
            state.parsed_problem,
            state.decomposed_tasks,
            state.selected_model,
            state.result_analysis,
            state.validation,
            state.generated_code,
            state.reports_dir,
            data_profile=state.data_profile,
            figure_plan=state.figure_plan,
            formulas=state.formulas,
        )
        self._log(paper_writer.name, {k: v for k, v in state.paper.items() if k != "markdown"})

        if self.enable_reflection:
            reflection_agent = ReflectionAgent(self.llm_client, state.logs_dir)
            state.reflection_report = reflection_agent.run(
                state.parsed_problem,
                state.decomposed_tasks,
                state.selected_model,
                state.generated_code,
                state.execution_result,
                state.figure_plan,
                state.validation,
                state.paper,
            )
            self._log(reflection_agent.name, state.reflection_report)
            if state.reflection_report.get("need_revision"):
                revision_agent = RevisionAgent(self.llm_client, state.logs_dir)
                revision = revision_agent.run(
                    state.reflection_report,
                    state.selected_model,
                    state.generated_code,
                    state.validation,
                    state.paper,
                )
                state.validation = revision.get("validation_results", state.validation)
                state.paper = revision.get("draft_report", state.paper)
                self._log(revision_agent.name, {k: v for k, v in revision.items() if k != "draft_report"})

            state.paper = paper_writer.run(
                state.parsed_problem,
                state.decomposed_tasks,
                state.selected_model,
                state.result_analysis,
                state.validation,
                state.generated_code,
                state.reports_dir,
                data_profile=state.data_profile,
                figure_plan=state.figure_plan,
                formulas=state.formulas,
                reflection_report=state.reflection_report,
            )
            self._log(f"{paper_writer.name}_final", {k: v for k, v in state.paper.items() if k != "markdown"})

        state.artifacts["report_path"] = state.paper.get("report_path")
        state.exports = self._export_reports(state)
        if state.exports:
            self._log("ReportExporter", state.exports)

        state.save_snapshot(state.logs_dir / "solver_state.json")
        return state

    def _execute_with_repair_loop(self, state: SolverState) -> None:
        executor = PythonExecutor(
            self.project_root,
            state.code_dir,
            timeout_seconds=120,
            logs_dir=state.logs_dir,
            figures_dir=state.figures_dir,
        )
        repair_agent = CodeRepairAgent(self.llm_client, state.logs_dir)
        code = state.generated_code["code"]
        repair_attempts: list[dict[str, Any]] = []
        code_file = executor.write_code("generated_solution.py", code)
        execution_result = executor.execute(code_file)
        execution_result["attempt"] = 0
        execution_result["repair"] = None
        state.execution_attempts.append(execution_result)
        self._log("execution_attempt_0", execution_result)

        state.execution_result = execution_result
        if not execution_result.get("success"):
            for repair_number in range(1, self.max_repairs + 1):
                repair = repair_agent.run(
                    original_code=code,
                    stderr=state.execution_result.get("stderr", ""),
                    stdout=state.execution_result.get("stdout", ""),
                    execution_context={
                        "attempt": repair_number,
                        "code_dir": str(state.code_dir),
                        "workspace_dir": str(state.output_dir / "code_workspace"),
                        "previous_returncode": state.execution_result.get("returncode"),
                        "safety": state.execution_result.get("safety", {}),
                    },
                    available_data_files=self._available_data_files(state.raw_data),
                    previous_repair_attempts=repair_attempts,
                )
                repair_attempts.append({k: v for k, v in repair.items() if k != "repaired_code"})
                self._log(f"{repair_agent.name}_{repair_number}", repair_attempts[-1])
                if not repair.get("changed"):
                    state.execution_result["repair_stopped_reason"] = "No deterministic repair changed the code."
                    break

                code = repair["repaired_code"]
                code_file = executor.write_code(f"attempt_{repair_number}.py", code)
                execution_result = executor.execute(code_file)
                execution_result["attempt"] = repair_number
                execution_result["repair"] = repair_attempts[-1]
                state.execution_attempts.append(execution_result)
                self._log(f"execution_attempt_{repair_number}", execution_result)
                state.execution_result = execution_result
                if execution_result.get("success"):
                    break

        write_json(state.logs_dir / "execution_attempts.json", state.execution_attempts)
        if state.execution_result.get("code_file"):
            state.artifacts["last_code_file"] = state.execution_result["code_file"]

    def _retrieve_rag(self, state: SolverState) -> list[dict[str, Any]]:
        query_parts = [
            state.parsed_problem.get("background", ""),
            state.parsed_problem.get("problem_type", ""),
            " ".join(str(item.get("text", "")) for item in state.parsed_problem.get("questions", [])),
        ]
        query = "\n".join(part for part in query_parts if part).strip()
        if not query:
            return []
        retriever = Retriever(self.kb_dir, logs_dir=state.logs_dir)
        return retriever.retrieve(query, top_k=5)

    def _export_reports(self, state: SolverState) -> dict[str, Any]:
        report_path = state.paper.get("report_path")
        if not report_path:
            return {}
        exporter = ReportExporter(state.reports_dir)
        return exporter.export_all(
            Path(report_path),
            export_docx=self.export_docx,
            export_pdf=self.export_pdf,
        )

    def _resolve_input(self, path: Path | str | None) -> Path | None:
        if path is None:
            return None
        path = Path(path)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def _available_data_files(self, raw_data: list[dict[str, Any]]) -> list[str]:
        files = []
        for item in raw_data:
            path = item.get("path")
            if path and path not in files:
                files.append(path)
        return files

    def _apply_solution_competition(
        self,
        selected_model: dict[str, Any],
        solution_competition: dict[str, Any],
    ) -> dict[str, Any]:
        selected_solution = solution_competition.get("selected_solution", {})
        selected_model["solution_competition"] = solution_competition
        selected_model["candidate_solutions"] = solution_competition.get("candidate_solutions", [])
        selected_model["selected_solution"] = selected_solution
        selected_model["selected_strategy"] = selected_solution
        if selected_solution:
            selected_model["overall_route"] = selected_solution.get("overall_idea", selected_model.get("overall_route", ""))
        return selected_model

    def _log(self, name: str, payload: dict[str, Any]) -> None:
        self.log_counter += 1
        write_json(self.output_dirs["logs_dir"] / f"{self.log_counter:03d}_{name}.json", payload)
