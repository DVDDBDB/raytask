import React, { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { UserAvatar } from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDateTime } from "@/lib/format";
import { toast } from "sonner";
import { Send, Plus } from "lucide-react";
import { MSG } from "@/constants/testIds";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import EmptyState from "@/components/EmptyState";

export default function Messages() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [users, setUsers] = useState([]);
  const [newOpen, setNewOpen] = useState(false);
  const [pickedIds, setPickedIds] = useState([]);
  const scrollRef = useRef(null);

  const loadConversations = () => api.get("/messages/conversations").then((r) => setConversations(r.data));
  useEffect(() => { loadConversations(); api.get("/users").then((r) => setUsers(r.data)); }, []);
  useEffect(() => {
    const iv = setInterval(loadConversations, 8000);
    return () => clearInterval(iv);
  }, []);

  const loadMessages = async (convId) => {
    const r = await api.get(`/messages/${convId}`);
    setMessages(r.data);
    setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 40);
  };

  useEffect(() => {
    if (!selected) return;
    loadMessages(selected.id);
    const iv = setInterval(() => loadMessages(selected.id), 4000);
    return () => clearInterval(iv);
  }, [selected]);

  const send = async () => {
    if (!text.trim() || !selected) return;
    const body = text.trim();
    setText("");
    // Optimistic append (real-time feel):
    const optimistic = {
      id: "temp-" + Date.now(),
      conversation_id: selected.id,
      sender_id: user.id,
      sender_first_name: user.first_name,
      sender_designation: user.designation,
      sender_avatar_url: user.avatar_url,
      body, created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 20);
    try {
      await api.post("/messages", { conversation_id: selected.id, body });
      loadMessages(selected.id);
      loadConversations();
    } catch (e) {
      toast.error("Failed to send");
    }
  };

  const startConversation = async () => {
    if (pickedIds.length === 0) { toast.error("Pick at least one teammate"); return; }
    const r = await api.post("/messages/conversations", { participant_ids: pickedIds });
    setSelected(r.data);
    setNewOpen(false);
    setPickedIds([]);
    loadConversations();
  };

  const other = (conv) => conv.participants?.find((p) => p?.id !== user.id) || conv.participants?.[0];

  return (
    <div className="space-y-4" data-testid="messages-page">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-overline">Team chat</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>Messages</h1>
        </div>
        <Button onClick={() => setNewOpen(true)} className="gap-2 rounded-full" data-testid={MSG.newConversation}>
          <Plus className="w-4 h-4" /> New chat
        </Button>
      </div>

      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-220px)] min-h-[400px]">
        <div className="col-span-4 card-flat overflow-y-auto">
          {conversations.length === 0 && (
            <div className="p-6 text-sm text-muted-foreground">No conversations yet.</div>
          )}
          {conversations.map((c) => {
            const o = other(c);
            const active = selected?.id === c.id;
            return (
              <button
                key={c.id}
                onClick={() => setSelected(c)}
                data-testid={`conv-${c.id}`}
                className={`w-full text-left px-4 py-3 border-b border-border flex items-center gap-3 transition-colors ${
                  active ? "bg-primary/10" : "hover:bg-muted"
                }`}
              >
                <UserAvatar user={o} size={36} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-semibold truncate">
                      {c.is_group ? (c.name || `Group (${c.participants.length})`) : (o?.first_name || "Unknown")}
                    </div>
                    {c.unread_count > 0 && (
                      <span className="text-[10px] bg-primary text-primary-foreground rounded-full px-1.5 py-0.5">
                        {c.unread_count}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-muted-foreground truncate">
                    {c.last_message?.body || "No messages"}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="col-span-8 card-flat flex flex-col">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
              Select a conversation to start chatting
            </div>
          ) : (
            <>
              <div className="p-4 border-b border-border">
                <div className="text-sm font-semibold">
                  {selected.is_group ? (selected.name || "Group") : other(selected)?.first_name}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {selected.participants.map((p) => p?.first_name).filter(Boolean).join(", ")}
                </div>
              </div>
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-2">
                {messages.map((m) => {
                  const mine = m.sender_id === user.id;
                  return (
                    <div key={m.id} className={`flex gap-2 ${mine ? "justify-end" : ""}`}>
                      {!mine && <UserAvatar user={{ first_name: m.sender_first_name, avatar_url: m.sender_avatar_url }} size={28} />}
                      <div className={`max-w-[70%] rounded-lg px-3 py-2 text-sm ${
                        mine ? "bg-primary text-primary-foreground" : "bg-muted"
                      }`}>
                        {!mine && (
                          <div className="text-[10px] font-semibold opacity-80 mb-0.5">
                            {m.sender_first_name} — {m.sender_designation}
                          </div>
                        )}
                        <div className="whitespace-pre-wrap">{m.body}</div>
                        <div className={`text-[10px] mt-1 ${mine ? "opacity-70" : "text-muted-foreground"}`}>
                          {formatDateTime(m.created_at)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="p-3 border-t border-border flex items-center gap-2">
                <Input
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
                  placeholder="Type a message…"
                  data-testid={MSG.input}
                />
                <Button onClick={send} className="gap-2" data-testid={MSG.sendButton}>
                  <Send className="w-4 h-4" /> Send
                </Button>
              </div>
            </>
          )}
        </div>
      </div>

      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle style={{ fontFamily: "Outfit" }}>Start a new chat</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {users.filter((u) => u.status === "active" && u.id !== user.id).map((u) => (
              <label key={u.id} className="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-muted">
                <Checkbox
                  checked={pickedIds.includes(u.id)}
                  onCheckedChange={(v) => setPickedIds(v ? [...pickedIds, u.id] : pickedIds.filter((x) => x !== u.id))}
                />
                <UserAvatar user={u} size={28} />
                <div>
                  <div className="text-sm font-medium">{u.first_name}</div>
                  <div className="text-[11px] text-muted-foreground">{u.designation}</div>
                </div>
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)}>Cancel</Button>
            <Button onClick={startConversation}>Start chat</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
