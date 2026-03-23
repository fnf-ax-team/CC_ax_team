---
name: frontend-patterns
description: Frontend development patterns for DCS-AI Next.js 15 client. Covers FSD architecture, Redux Toolkit, SWR, HTTP streaming, and React 19 patterns.
---

# Frontend Development Patterns for DCS-AI

Modern frontend patterns for Next.js 15, React 19, Redux Toolkit, and SWR.

## Feature-Sliced Design (FSD) Architecture

### Layer Hierarchy

```
client/src/
├── app/          # Next.js App Router + global providers
├── pages/        # Page components (screen layouts)
├── widgets/      # Complex composite UI (ChatSidebar, Header)
├── features/     # User interactions (useChatInput, useMessageSend)
├── entities/     # Business entities (chat, user, mcp-server)
└── shared/       # Shared utilities, UI kit, API client
```

**Import Rule**: Higher layers import from lower layers ONLY.
- ✅ `features/` → `entities/` → `shared/`
- ❌ `entities/` → `features/` (NEVER)

### Entity Structure

```
client/src/entities/chat/
├── model/
│   ├── types.ts       # TypeScript interfaces
│   └── store.ts       # Redux slice (if needed)
├── api/
│   └── chat-api.ts    # API functions
└── ui/
    ├── ChatMessage.tsx
    └── ChatList.tsx
```

## API Client Pattern

### Using apiClient (shared/api/client.ts)

```typescript
import { apiClient } from '@/shared/api/client';

// GET request
const chats = await apiClient.fetcher('/chat');

// POST with body
const response = await apiClient.fetcherRaw('/chat/message', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ content, chatId }),
});

// File download
const blob = await apiClient.downloadFile('/export/chat/123');

// IMPORTANT: credentials: 'include' is automatic for JWT cookies
```

## State Management

### Redux Toolkit for Global State

```typescript
// client/src/shared/model/store.ts
import { configureStore } from '@reduxjs/toolkit';
import chatReducer from '@/entities/chat/model/store';
import uiReducer from '@/shared/model/ui-slice';

export const store = configureStore({
  reducer: {
    chat: chatReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

### Chat Slice

```typescript
// client/src/entities/chat/model/store.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ChatState {
  currentChatId: string | null;
  isStreaming: boolean;
  pendingMessage: string;
}

const initialState: ChatState = {
  currentChatId: null,
  isStreaming: false,
  pendingMessage: '',
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setCurrentChat: (state, action: PayloadAction<string | null>) => {
      state.currentChatId = action.payload;
    },
    setStreaming: (state, action: PayloadAction<boolean>) => {
      state.isStreaming = action.payload;
    },
    setPendingMessage: (state, action: PayloadAction<string>) => {
      state.pendingMessage = action.payload;
    },
  },
});

export const { setCurrentChat, setStreaming, setPendingMessage } = chatSlice.actions;
export default chatSlice.reducer;
```

### Typed Hooks

```typescript
// client/src/shared/model/hooks.ts
import { useDispatch, useSelector, TypedUseSelectorHook } from 'react-redux';
import type { RootState, AppDispatch } from './store';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

## SWR for Server State

### Basic Usage

```typescript
// client/src/entities/chat/api/chat-api.ts
import useSWR from 'swr';
import { apiClient } from '@/shared/api/client';
import { Chat, ChatMessage } from '../model/types';

export function useChats() {
  const { data, error, mutate, isLoading } = useSWR<Chat[]>(
    '/chat',
    apiClient.fetcher
  );

  return {
    chats: data,
    isLoading,
    isError: error,
    mutate,
  };
}

export function useChatMessages(chatId: string | null) {
  const { data, error, mutate, isLoading } = useSWR<ChatMessage[]>(
    chatId ? `/chat/${chatId}/messages` : null,
    apiClient.fetcher
  );

  return {
    messages: data,
    isLoading,
    isError: error,
    mutate,
  };
}
```

### Optimistic Updates

```typescript
export function useSendMessage(chatId: string) {
  const { mutate } = useChatMessages(chatId);

  const sendMessage = async (content: string) => {
    // Optimistic update
    const optimisticMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      content,
      role: 'user',
      createdAt: new Date().toISOString(),
    };

    mutate(
      async (currentMessages) => {
        // Add optimistic message
        const updated = [...(currentMessages || []), optimisticMessage];
        
        // Send to server
        await apiClient.fetcherRaw(`/chat/${chatId}/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content }),
        });

        // Return updated list (server response will be fetched on revalidate)
        return updated;
      },
      { optimisticData: (current) => [...(current || []), optimisticMessage] }
    );
  };

  return { sendMessage };
}
```

## HTTP Streaming for AI Responses

### useStreamingChat Hook

```typescript
// client/src/features/chat/model/use-streaming-chat.ts
import { useState, useCallback } from 'react';
import { useAppDispatch } from '@/shared/model/hooks';
import { setStreaming } from '@/entities/chat/model/store';

export function useStreamingChat(chatId: string) {
  const dispatch = useAppDispatch();
  const [streamingContent, setStreamingContent] = useState('');

  const sendMessage = useCallback(async (content: string) => {
    dispatch(setStreaming(true));
    setStreamingContent('');

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ content, chatId }),
      });

      if (!response.ok) throw new Error('Stream failed');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;

            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                setStreamingContent((prev) => prev + parsed.content);
              }
            } catch {
              // Ignore parse errors for partial chunks
            }
          }
        }
      }
    } finally {
      dispatch(setStreaming(false));
    }
  }, [chatId, dispatch]);

  return { sendMessage, streamingContent };
}
```

## Component Patterns

### Feature Component (with hooks)

```typescript
// client/src/features/chat/ui/ChatInput.tsx
'use client';

import { useState } from 'react';
import { useAppSelector } from '@/shared/model/hooks';
import { useStreamingChat } from '../model/use-streaming-chat';
import { Button } from '@/shared/ui/button';
import { Textarea } from '@/shared/ui/textarea';

interface Props {
  chatId: string;
}

export function ChatInput({ chatId }: Props) {
  const [message, setMessage] = useState('');
  const isStreaming = useAppSelector((state) => state.chat.isStreaming);
  const { sendMessage } = useStreamingChat(chatId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isStreaming) return;

    const content = message;
    setMessage('');
    await sendMessage(content);
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type a message..."
        disabled={isStreaming}
        data-testid="chat-input"
      />
      <Button 
        type="submit" 
        disabled={!message.trim() || isStreaming}
        data-testid="send-button"
      >
        {isStreaming ? 'Sending...' : 'Send'}
      </Button>
    </form>
  );
}
```

### Entity Component (presentational)

```typescript
// client/src/entities/chat/ui/ChatMessage.tsx
import { cn } from '@/shared/lib/utils';
import { ChatMessage as ChatMessageType } from '../model/types';

interface Props {
  message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'p-4 rounded-lg',
        isUser ? 'bg-blue-100 ml-auto' : 'bg-gray-100'
      )}
      data-testid={`message-${message.role}`}
    >
      <p className="text-sm font-medium mb-1">
        {isUser ? 'You' : 'AI Assistant'}
      </p>
      <p className="whitespace-pre-wrap">{message.content}</p>
    </div>
  );
}
```

## NextAuth Integration

### useSession Hook

```typescript
// Using NextAuth session in components
import { useSession } from 'next-auth/react';

export function UserMenu() {
  const { data: session, status } = useSession();

  if (status === 'loading') {
    return <Skeleton />;
  }

  if (!session) {
    return <LoginButton />;
  }

  return (
    <div data-testid="user-menu">
      <span>{session.user?.name}</span>
      <LogoutButton />
    </div>
  );
}
```

### Protected Page

```typescript
// client/src/app/chat/page.tsx
import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';
import { ChatPage } from '@/pages/chat';

export default async function Chat() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect('/login');
  }

  return <ChatPage />;
}
```

## Custom Hooks Patterns

### useDebounce

```typescript
// client/src/shared/lib/hooks/use-debounce.ts
import { useState, useEffect } from 'react';

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

// Usage
const [searchQuery, setSearchQuery] = useState('');
const debouncedQuery = useDebounce(searchQuery, 500);

useEffect(() => {
  if (debouncedQuery) {
    searchChats(debouncedQuery);
  }
}, [debouncedQuery]);
```

### useLocalStorage

```typescript
// client/src/shared/lib/hooks/use-local-storage.ts
import { useState, useEffect } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(initialValue);

  useEffect(() => {
    try {
      const item = window.localStorage.getItem(key);
      if (item) {
        setStoredValue(JSON.parse(item));
      }
    } catch (error) {
      console.error('Error reading localStorage:', error);
    }
  }, [key]);

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error('Error setting localStorage:', error);
    }
  };

  return [storedValue, setValue] as const;
}
```

## Performance Optimization

### Memoization

```typescript
import { useMemo, useCallback, memo } from 'react';

// useMemo for expensive computations
const sortedMessages = useMemo(() => {
  return messages?.sort((a, b) => 
    new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  );
}, [messages]);

// useCallback for functions passed to children
const handleMessageClick = useCallback((id: string) => {
  setSelectedMessage(id);
}, []);

// memo for pure components
export const ChatMessage = memo<ChatMessageProps>(({ message }) => {
  return <div>{message.content}</div>;
});
```

### Lazy Loading

```typescript
import { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

export function ChatPage() {
  return (
    <div>
      <ChatMessages />
      <Suspense fallback={<Skeleton />}>
        <HeavyComponent />
      </Suspense>
    </div>
  );
}
```

## Error Handling

### Error Boundary

```typescript
// client/src/shared/ui/error-boundary.tsx
'use client';

import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-4 text-red-500">
          Something went wrong. Please try again.
        </div>
      );
    }

    return this.props.children;
  }
}
```

## Best Practices

1. **Follow FSD** - Higher layers import from lower only
2. **Use shared UI first** - Check `@/shared/ui` before creating new components
3. **Redux for global state** - SWR for server state
4. **Always include credentials** - `credentials: 'include'` for JWT
5. **Stream AI responses** - Use HTTP streaming, not WebSocket
6. **Memoize expensive ops** - useMemo, useCallback, memo
7. **Type everything** - Full TypeScript coverage
8. **Test with data-testid** - Add test IDs for Playwright

**Remember**: Modern frontend patterns enable maintainable, performant user interfaces.
