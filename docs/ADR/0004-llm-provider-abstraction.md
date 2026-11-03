# ADR 0004: Pluggable `LLMProvider` Abstraction with Pydantic JSON Schema Validation

- **Status**: Accepted
- **Date**: 2026-11-03
- **Deciders**: Full-Stack Architecture Team

---

## Context and Problem Statement
The curation engine relies on Large Language Models to convert prompts into search plans and rank video candidates. We must support free default cloud providers (Gemini 2.5 Flash), local offline models (Ollama), and optional commercial providers (Anthropic, OpenAI) without coupling core logic to vendor SDKs.

## Decision Drivers
- Free-tier accessibility out of the box with zero required credit cards.
- Support for offline local execution where feasible.
- Strict type-safety and hallucination prevention (rejecting invalid models or fake IDs).
- Deterministic testing without external network dependencies.

## Considered Options
- **Option 1**: Directly integrate `google-genai` SDK in worker business logic.
- **Option 2**: Use LangChain / LlamaIndex framework.
- **Option 3**: Build a minimal, typed `LLMProvider` abstract base class with Pydantic JSON schema structured generation.

## Decision Outcome
Chosen option: **Option 3: Minimal, typed `LLMProvider` abstract base class with Pydantic JSON schema structured generation**.

### Rationale:
- Vendor SDK coupling prevents offline testing and portability.
- Frameworks like LangChain add immense dependency bloat (~100+ packages), breaking our memory budget on the 2 GB NAS.
- A concise interface:
  ```python
  class LLMProvider(ABC):
      @abstractmethod
      async def generate_structured(
          self,
          system: str,
          user: str,
          schema: type[T],
          *,
          temperature: float = 0.2,
      ) -> T: ...
  ```
  allows clean implementation of:
  - `GeminiProvider`: Uses Gemini Flash free tier with `response_mime_type="application/json"` and `response_schema`.
  - `OllamaProvider`: Connects to local Ollama with `format=schema.model_json_schema()`.
  - `FakeLLMProvider`: Deterministic, reads recorded golden fixtures from `seed/fixtures/` for unit, contract, and e2e tests.

## Consequences
- **Positive**: Zero bloat; instant provider swapping via `LLM_PROVIDER` env variable; 100% deterministic test suite.
- **Negative**: Must implement lightweight adapters for each supported provider.
