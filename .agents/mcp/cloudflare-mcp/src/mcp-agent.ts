/**
 * CurLexAI MCP Agent — exposes Mihwar (architect) and Bayyinah (validator)
 * as remote MCP tools via Cloudflare Workers.
 *
 * Tools are read-only proxies to the private Modal runtime.
 * Modal endpoint URLs never leave the server side.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { McpAgent } from "agents/mcp";
import { z } from "zod";
import { mihwarGenerate, bayyinahReview } from "./modal-client";

export type Props = {
  login: string;
  name: string;
  email: string;
  accessToken: string;
};

export class AgentMCP extends McpAgent<Env, {}, Props> {
  server = new McpServer({
    name: "CurLexAI Agent Operations",
    version: "1.0.0",
  });

  private modalConfig() {
    return {
      mihwarEndpoint: this.env.MIHWAR_ENDPOINT ?? "",
      bayyinahEndpoint: this.env.BAYYINAH_ENDPOINT ?? "",
      mihwarApiToken: this.env.MIHWAR_API_TOKEN ?? "",
      bayyinahApiToken: this.env.BAYYINAH_API_TOKEN ?? "",
    };
  }

  async init() {
    this.server.tool(
      "mihwar_generate",
      "Generate code or architectural plans using the Mihwar agent (DeepSeek-Coder-V2-Instruct). " +
        "Mihwar is the Tier-1 architect/generator in the CurLexAI agent topology.",
      {
        task: z.string().describe("Description of the coding or architecture task"),
        code: z
          .string()
          .optional()
          .describe("Existing code to refactor, extend, or use as context"),
        context: z
          .string()
          .optional()
          .describe("Additional context such as requirements, constraints, or repo structure"),
      },
      async ({ task, code, context }) => {
        const result = await mihwarGenerate(this.modalConfig(), task, code, context);

        if (!result.ok) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Error: ${result.error.message}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [{ type: "text" as const, text: result.value.output }],
        };
      },
    );

    this.server.tool(
      "bayyinah_review",
      "Review code using the Bayyinah agent (Qwen2.5-Coder-32B-Instruct). " +
        "Bayyinah is the Tier-2 reviewer/validator. It checks for security issues, " +
        "code quality, and compliance. It must never approve with unresolved CRITICAL/HIGH findings.",
      {
        code: z.string().describe("Code to review"),
        context: z
          .string()
          .optional()
          .describe("Review context such as PR description, requirements, or focus areas"),
      },
      async ({ code, context }) => {
        const result = await bayyinahReview(this.modalConfig(), code, context);

        if (!result.ok) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Error: ${result.error.message}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [{ type: "text" as const, text: result.value.output }],
        };
      },
    );

    this.server.tool(
      "agent_info",
      "List the configured CurLexAI agents, their models, roles, and tiers.",
      {},
      async () => {
        const agents = [
          {
            name: "Mihwar (المحور)",
            model: "DeepSeek-Coder-V2-Instruct",
            role: "Architect / generator",
            tier: 1,
            runtime: "Modal + vLLM",
            configured: !!this.env.MIHWAR_ENDPOINT,
          },
          {
            name: "Bayyinah (البيّنة)",
            model: "Qwen2.5-Coder-32B-Instruct",
            role: "Reviewer / validator",
            tier: 2,
            runtime: "Modal + vLLM",
            configured: !!this.env.BAYYINAH_ENDPOINT,
          },
          {
            name: "Copilot SWE",
            model: "GitHub Copilot",
            role: "Scaffold-only executor",
            tier: 3,
            runtime: "GitHub Actions",
            configured: true,
          },
        ];

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  agents,
                  collaboration:
                    "Mihwar generates → Bayyinah reviews → up to 3 revision cycles → human approval",
                },
                null,
                2,
              ),
            },
          ],
        };
      },
    );

    this.server.tool(
      "pipeline",
      "Run the full Mihwar→Bayyinah pipeline: Mihwar generates a solution, " +
        "then Bayyinah reviews it. Returns both the generated output and the review.",
      {
        task: z.string().describe("Description of the coding task for Mihwar to generate"),
        code: z.string().optional().describe("Existing code to refactor or extend"),
        context: z.string().optional().describe("Additional context or requirements"),
      },
      async ({ task, code, context }) => {
        const cfg = this.modalConfig();

        const genResult = await mihwarGenerate(cfg, task, code, context);
        if (!genResult.ok) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Mihwar generation failed: ${genResult.error.message}`,
              },
            ],
            isError: true,
          };
        }

        const reviewResult = await bayyinahReview(
          cfg,
          genResult.value.output,
          `Task: ${task}\n${context ?? ""}`,
        );

        if (!reviewResult.ok) {
          return {
            content: [
              {
                type: "text" as const,
                text: [
                  "## Mihwar Generation (Success)",
                  genResult.value.output,
                  "",
                  "## Bayyinah Review (Failed)",
                  reviewResult.error.message,
                ].join("\n"),
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text" as const,
              text: [
                "## Mihwar Generation",
                genResult.value.output,
                "",
                "## Bayyinah Review",
                reviewResult.value.output,
              ].join("\n"),
            },
          ],
        };
      },
    );

    this.server.tool(
      "whoami",
      "Show the authenticated GitHub user connected to this MCP session.",
      {},
      async () => {
        const { login, name, email } = this.props!;
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                { login, name, email },
                null,
                2,
              ),
            },
          ],
        };
      },
    );
  }
}
