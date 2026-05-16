import { createHash } from 'node:crypto';
import { mkdir, appendFile, readFile } from 'node:fs/promises';
import { dirname } from 'node:path';

/**
 * Append-only audit event stored as NDJSON with hash chaining.
 */
export interface AppendOnlyAuditEvent {
  readonly traceId: string;
  readonly agentId: string;
  readonly stage: string;
  readonly timestamp: string;
  readonly payload: Readonly<Record<string, string | number | boolean | null>>;
}

/**
 * Stored record format for the append-only sink.
 */
export interface AppendOnlyAuditRecord {
  readonly sequence: number;
  readonly previousHash: string | null;
  readonly recordHash: string;
  readonly event: AppendOnlyAuditEvent;
}

/**
 * File-backed append-only sink for Bayyinah local verification and diagnostics.
 */
export class AppendOnlyFileAuditSink {
  private readonly filePath: string;

  public constructor(filePath: string) {
    this.filePath = filePath;
  }

  /**
   * Append a new event to the ledger.
   */
  public async append(event: AppendOnlyAuditEvent): Promise<AppendOnlyAuditRecord> {
    const records = await this.listAll();
    const previousRecord = records.at(-1) ?? null;
    const nextRecord: AppendOnlyAuditRecord = {
      sequence: previousRecord === null ? 1 : previousRecord.sequence + 1,
      previousHash: previousRecord?.recordHash ?? null,
      recordHash: 'pending',
      event
    };

    const recordHash = this.hashRecord({
      ...nextRecord,
      recordHash: 'pending'
    });

    const finalizedRecord: AppendOnlyAuditRecord = {
      ...nextRecord,
      recordHash
    };

    await mkdir(dirname(this.filePath), { recursive: true });
    await appendFile(this.filePath, `${JSON.stringify(finalizedRecord)}\n`, 'utf8');

    return finalizedRecord;
  }

  /**
   * List all records from the ledger.
   */
  public async listAll(): Promise<readonly AppendOnlyAuditRecord[]> {
    try {
      const content = await readFile(this.filePath, 'utf8');
      const lines = content
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

      return lines.map((line) => this.parseRecord(line));
    } catch (error: unknown) {
      if (error instanceof Error && 'code' in error && error.code === 'ENOENT') {
        return [];
      }

      throw error;
    }
  }

  /**
   * Verify full chain integrity.
   */
  public async verifyChain(): Promise<boolean> {
    const records = await this.listAll();

    for (let index = 0; index < records.length; index += 1) {
      const current = records[index];
      const expectedPreviousHash = index === 0 ? null : records[index - 1].recordHash;

      if (current.previousHash !== expectedPreviousHash) {
        return false;
      }

      const computedHash = this.hashRecord({
        ...current,
        recordHash: 'pending'
      });

      if (computedHash !== current.recordHash) {
        return false;
      }
    }

    return true;
  }

  private parseRecord(raw: string): AppendOnlyAuditRecord {
    const parsed = JSON.parse(raw) as {
      readonly sequence: number;
      readonly previousHash: string | null;
      readonly recordHash: string;
      readonly event: AppendOnlyAuditEvent;
    };

    return {
      sequence: parsed.sequence,
      previousHash: parsed.previousHash,
      recordHash: parsed.recordHash,
      event: parsed.event
    };
  }

  private hashRecord(record: Omit<AppendOnlyAuditRecord, 'recordHash'> & { readonly recordHash: string }): string {
    const canonical = JSON.stringify({
      sequence: record.sequence,
      previousHash: record.previousHash,
      event: record.event
    });

    return createHash('sha256').update(canonical).digest('hex');
  }
}
