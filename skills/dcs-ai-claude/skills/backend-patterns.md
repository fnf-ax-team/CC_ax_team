---
name: backend-patterns
description: Backend architecture patterns for DCS-AI NestJS server. Covers TypeORM, PostgreSQL, Snowflake analytics, HTTP streaming, and MCP tool integration.
---

# Backend Development Patterns for DCS-AI

Backend architecture patterns for the NestJS server with TypeORM, PostgreSQL, and MCP integration.

## NestJS Module Pattern

### Standard Module Structure

```typescript
// server/src/chat/chat.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ChatController } from './chat.controller';
import { ChatService } from './chat.service';
import { ChatMessage } from '../database/entities/chat-message.entity';
import { Chat } from '../database/entities/chat.entity';

@Module({
  imports: [
    TypeOrmModule.forFeature([Chat, ChatMessage]),
  ],
  controllers: [ChatController],
  providers: [ChatService],
  exports: [ChatService],
})
export class ChatModule {}
```

### Controller Pattern

```typescript
// server/src/chat/chat.controller.ts
import { Controller, Get, Post, Body, Param, UseGuards, Request, Res } from '@nestjs/common';
import { Response } from 'express';
import { NextAuthGuard } from '../auth/guards/next-auth.guard';
import { ChatService } from './chat.service';
import { CreateMessageDto } from './dto/create-message.dto';

@Controller('chat')
@UseGuards(NextAuthGuard)
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Get()
  async getChats(@Request() req) {
    return this.chatService.getUserChats(req.user.id);
  }

  @Get(':id')
  async getChat(@Param('id') chatId: string, @Request() req) {
    return this.chatService.getChatWithMessages(chatId, req.user.id);
  }

  @Post('message')
  async createMessage(@Body() dto: CreateMessageDto, @Request() req) {
    return this.chatService.createMessage({
      ...dto,
      userId: req.user.id,
    });
  }

  // HTTP Streaming for AI responses
  @Post('stream')
  async streamChat(@Body() dto: CreateMessageDto, @Request() req, @Res() res: Response) {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Transfer-Encoding', 'chunked');

    try {
      for await (const chunk of this.chatService.streamResponse(dto, req.user.id)) {
        res.write(`data: ${JSON.stringify(chunk)}\n\n`);
      }
      res.write('data: [DONE]\n\n');
    } catch (error) {
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
    } finally {
      res.end();
    }
  }
}
```

### Service Pattern

```typescript
// server/src/chat/chat.service.ts
import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Chat } from '../database/entities/chat.entity';
import { ChatMessage } from '../database/entities/chat-message.entity';

@Injectable()
export class ChatService {
  constructor(
    @InjectRepository(Chat)
    private chatRepo: Repository<Chat>,
    @InjectRepository(ChatMessage)
    private messageRepo: Repository<ChatMessage>,
  ) {}

  async getUserChats(userId: string): Promise<Chat[]> {
    return this.chatRepo.find({
      where: { userId },
      order: { updatedAt: 'DESC' },
    });
  }

  async getChatWithMessages(chatId: string, userId: string): Promise<Chat> {
    const chat = await this.chatRepo.findOne({
      where: { id: chatId },
      relations: ['messages'],
    });

    if (!chat) {
      throw new NotFoundException('Chat not found');
    }

    if (chat.userId !== userId) {
      throw new ForbiddenException('Access denied');
    }

    return chat;
  }

  async createMessage(data: CreateMessageDto & { userId: string }): Promise<ChatMessage> {
    // Verify chat ownership
    const chat = await this.chatRepo.findOne({
      where: { id: data.chatId },
    });

    if (!chat || chat.userId !== data.userId) {
      throw new ForbiddenException('Access denied');
    }

    const message = this.messageRepo.create({
      content: data.content,
      role: 'user',
      chatId: data.chatId,
    });

    return this.messageRepo.save(message);
  }

  async *streamResponse(dto: CreateMessageDto, userId: string): AsyncGenerator<any> {
    // AI streaming implementation
    // Use LangChain or AI SDK for actual streaming
    yield { type: 'start' };
    
    // Stream chunks from AI
    for await (const chunk of this.aiService.stream(dto.content)) {
      yield { type: 'chunk', content: chunk };
    }
    
    yield { type: 'end' };
  }
}
```

## TypeORM Entity Patterns

### Base Entity

```typescript
// server/src/database/entities/base.entity.ts
import { 
  PrimaryGeneratedColumn, 
  CreateDateColumn, 
  UpdateDateColumn 
} from 'typeorm';

export abstract class BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
```

### Chat Entity

```typescript
// server/src/database/entities/chat.entity.ts
import { Entity, Column, OneToMany, Index } from 'typeorm';
import { BaseEntity } from './base.entity';
import { ChatMessage } from './chat-message.entity';

@Entity('chats')
export class Chat extends BaseEntity {
  @Column()
  @Index()
  userId: string;

  @Column({ nullable: true })
  title: string;

  @OneToMany(() => ChatMessage, message => message.chat)
  messages: ChatMessage[];
}
```

### Chat Message Entity

```typescript
// server/src/database/entities/chat-message.entity.ts
import { Entity, Column, ManyToOne, JoinColumn, Index } from 'typeorm';
import { BaseEntity } from './base.entity';
import { Chat } from './chat.entity';

@Entity('chat_messages')
export class ChatMessage extends BaseEntity {
  @Column('text')
  content: string;

  @Column({
    type: 'enum',
    enum: ['user', 'assistant', 'system'],
    default: 'user',
  })
  role: 'user' | 'assistant' | 'system';

  @Column({ nullable: true })
  @Index()
  chatId: string;

  @ManyToOne(() => Chat, chat => chat.messages, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'chatId' })
  chat: Chat;

  @Column({ type: 'jsonb', nullable: true })
  metadata: Record<string, any>;
}
```

## Repository Patterns

### Query Builder Usage

```typescript
// Complex queries with QueryBuilder
async searchMessages(userId: string, query: string): Promise<ChatMessage[]> {
  return this.messageRepo
    .createQueryBuilder('message')
    .innerJoin('message.chat', 'chat')
    .where('chat.userId = :userId', { userId })
    .andWhere('message.content ILIKE :query', { query: `%${query}%` })
    .orderBy('message.createdAt', 'DESC')
    .limit(50)
    .getMany();
}

// Pagination
async getChatMessages(
  chatId: string, 
  page: number = 1, 
  limit: number = 50
): Promise<{ messages: ChatMessage[]; total: number }> {
  const [messages, total] = await this.messageRepo.findAndCount({
    where: { chatId },
    order: { createdAt: 'ASC' },
    skip: (page - 1) * limit,
    take: limit,
  });

  return { messages, total };
}
```

### Transaction Pattern

```typescript
// Atomic operations with transactions
async createChatWithFirstMessage(
  userId: string, 
  content: string
): Promise<Chat> {
  return this.dataSource.transaction(async (manager) => {
    const chatRepo = manager.getRepository(Chat);
    const messageRepo = manager.getRepository(ChatMessage);

    // Create chat
    const chat = chatRepo.create({ userId, title: content.slice(0, 50) });
    await chatRepo.save(chat);

    // Create first message
    const message = messageRepo.create({
      chatId: chat.id,
      content,
      role: 'user',
    });
    await messageRepo.save(message);

    return chat;
  });
}
```

## Snowflake Integration (Analytics)

```typescript
// server/src/database/snowflake.service.ts
import { Injectable } from '@nestjs/common';
import * as snowflake from 'snowflake-sdk';

@Injectable()
export class SnowflakeService {
  private connection: snowflake.Connection;

  async execute<T>(query: string, binds: any[] = []): Promise<T[]> {
    return new Promise((resolve, reject) => {
      this.connection.execute({
        sqlText: query,
        binds,
        complete: (err, stmt, rows) => {
          if (err) reject(err);
          else resolve(rows as T[]);
        },
      });
    });
  }

  // Analytics queries only - NOT for primary data
  async getChatAnalytics(userId: string): Promise<any> {
    return this.execute(`
      SELECT 
        DATE_TRUNC('day', created_at) as date,
        COUNT(*) as message_count
      FROM analytics.chat_messages
      WHERE user_id = ?
      GROUP BY date
      ORDER BY date DESC
      LIMIT 30
    `, [userId]);
  }
}
```

## MCP Tool Integration

### MCP Service

```typescript
// server/src/mcp/mcp.service.ts
import { Injectable, BadRequestException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { McpServer } from '../database/entities/mcp-server.entity';

@Injectable()
export class McpService {
  private toolClients: Map<string, any> = new Map();

  constructor(
    @InjectRepository(McpServer)
    private mcpServerRepo: Repository<McpServer>,
  ) {}

  async getAvailableTools(userId: string): Promise<McpServer[]> {
    return this.mcpServerRepo.find({
      where: { isActive: true },
    });
  }

  async executeTool(
    userId: string,
    serverId: string,
    toolName: string,
    params: unknown
  ): Promise<any> {
    const server = await this.mcpServerRepo.findOne({
      where: { id: serverId, isActive: true },
    });

    if (!server) {
      throw new BadRequestException('MCP server not found');
    }

    // Get or create tool client
    const client = await this.getToolClient(server);

    // Execute with timeout
    const result = await Promise.race([
      client.callTool(toolName, params),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Tool timeout')), 30000)
      ),
    ]);

    return result;
  }

  private async getToolClient(server: McpServer): Promise<any> {
    if (this.toolClients.has(server.id)) {
      return this.toolClients.get(server.id);
    }

    // Initialize MCP client based on server config
    const client = await this.initializeClient(server);
    this.toolClients.set(server.id, client);

    return client;
  }
}
```

## Error Handling

### Global Exception Filter

```typescript
// server/src/common/filters/http-exception.filter.ts
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { Response } from 'express';

@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message = 'Internal server error';

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const exceptionResponse = exception.getResponse();
      message = typeof exceptionResponse === 'string' 
        ? exceptionResponse 
        : (exceptionResponse as any).message;
    }

    // Log error (don't expose details in production)
    console.error('Error:', exception);

    response.status(status).json({
      success: false,
      statusCode: status,
      message,
      timestamp: new Date().toISOString(),
    });
  }
}
```

### DTO Validation

```typescript
// server/src/chat/dto/create-message.dto.ts
import { IsString, IsNotEmpty, IsUUID, MaxLength } from 'class-validator';

export class CreateMessageDto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(10000)
  content: string;

  @IsUUID()
  chatId: string;
}

// Enable validation globally in main.ts
app.useGlobalPipes(new ValidationPipe({
  whitelist: true,
  forbidNonWhitelisted: true,
  transform: true,
}));
```

## Caching with Redis

```typescript
// server/src/common/cache/cache.service.ts
import { Injectable, Inject, CACHE_MANAGER } from '@nestjs/common';
import { Cache } from 'cache-manager';

@Injectable()
export class CacheService {
  constructor(@Inject(CACHE_MANAGER) private cacheManager: Cache) {}

  async get<T>(key: string): Promise<T | null> {
    return this.cacheManager.get<T>(key);
  }

  async set(key: string, value: any, ttl: number = 300): Promise<void> {
    await this.cacheManager.set(key, value, ttl);
  }

  async del(key: string): Promise<void> {
    await this.cacheManager.del(key);
  }

  // Cache decorator pattern
  async getOrSet<T>(
    key: string, 
    factory: () => Promise<T>, 
    ttl: number = 300
  ): Promise<T> {
    const cached = await this.get<T>(key);
    if (cached) return cached;

    const value = await factory();
    await this.set(key, value, ttl);
    return value;
  }
}

// Usage
async getChat(chatId: string): Promise<Chat> {
  return this.cacheService.getOrSet(
    `chat:${chatId}`,
    () => this.chatRepo.findOne({ where: { id: chatId } }),
    300 // 5 minutes
  );
}
```

## Rate Limiting

```typescript
// server/src/common/guards/rate-limit.guard.ts
import { Injectable, CanActivate, ExecutionContext, HttpException } from '@nestjs/common';
import { CacheService } from '../cache/cache.service';

@Injectable()
export class RateLimitGuard implements CanActivate {
  constructor(private cacheService: CacheService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const userId = request.user?.id || request.ip;
    const key = `ratelimit:${userId}`;

    const current = await this.cacheService.get<number>(key) || 0;

    if (current >= 100) { // 100 requests per minute
      throw new HttpException('Rate limit exceeded', 429);
    }

    await this.cacheService.set(key, current + 1, 60);
    return true;
  }
}
```

## Best Practices

1. **Always use guards** on protected routes
2. **Validate all inputs** with class-validator DTOs
3. **Use transactions** for multi-step operations
4. **Cache expensive queries** with Redis
5. **Stream AI responses** with chunked transfer encoding
6. **PostgreSQL for system data**, Snowflake for analytics only
7. **Log errors** but don't expose details to clients
8. **Rate limit** API endpoints

**Remember**: Backend patterns enable scalable, secure, and maintainable server-side applications.
