from hikkatl.types import Message, PeerUser, PeerChat, PeerChannel
from .. import loader, utils

from collections import defaultdict
import matplotlib.pyplot as plt
import io
import asyncio
import warnings
import numpy as np
import math
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
from telethon.tl.functions.messages import SearchRequest, GetHistoryRequest
from telethon.tl.types import InputMessagesFilterEmpty

@loader.tds
class EnhancedTop(loader.Module):
    """Advanced module for viewing top users in chats with beautiful visualization"""
    strings = {
        "name": "EnhancedTop",
        "top": "Top users by message count",
        "topchat": "<emoji document_id=5323538339062628165>💬</emoji><b>Top users in</b>",
        "msgcount": "Message count",
        "loading": "<emoji document_id=5780543148782522693>🕒</emoji><b>Message counting started, please wait...</b>",
        "progress": "<emoji document_id=5780543148782522693>🕒</emoji><b>Progress: {progress}%</b>",
        "private_chat": "<emoji document_id=5323538339062628165>💬</emoji><b>Message count in private chat with</b>",
        "no_messages": "<emoji document_id=5312526098750252863>❌</emoji><b>No messages found in this chat</b>",
        "limit_exceeded": "<emoji document_id=5312526098750252863>❌</emoji><b>Too many users in chat. Showing top {limit} users</b>",
        "top_file": "<emoji document_id=5323538339062628165>💬</emoji><b>Chat statistics as CSV file</b>",
        "activity_title": "Chat Activity Analysis",
        "activity_desc": "Message frequency distribution"
    }

    strings_ru = {
        "top": "Топ пользователей по количеству сообщений",
        "topchat": "<emoji document_id=5323538339062628165>💬</emoji><b>Топ пользователей в</b>",
        "msgcount": "Количество сообщений",
        "loading": "<emoji document_id=5780543148782522693>🕒</emoji><b>Подсчет сообщений начался, пожалуйста подождите...</b>",
        "progress": "<emoji document_id=5780543148782522693>🕒</emoji><b>Прогресс: {progress}%</b>",
        "private_chat": "<emoji document_id=5323538339062628165>💬</emoji><b>Количество сообщений в личном чате с</b>",
        "no_messages": "<emoji document_id=5312526098750252863>❌</emoji><b>Сообщений в этом чате не найдено</b>",
        "limit_exceeded": "<emoji document_id=5312526098750252863>❌</emoji><b>Слишком много пользователей в чате. Показаны топ {limit} пользователей</b>",
        "top_file": "<emoji document_id=5323538339062628165>💬</emoji><b>Статистика чата в формате CSV</b>",
        "activity_title": "Анализ активности в чате",
        "activity_desc": "Распределение частоты сообщений"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "TOP_LIMIT", 20, "Maximum number of users to show in top list",
            "GRADIENT_START", "#9C27B0", "Start color for gradient (hex)",
            "GRADIENT_END", "#3F51B5", "End color for gradient (hex)",
            "TOP_HIGHLIGHT", "#FFD700", "Color for top 3 users (hex)",
            "ENABLE_ANIMATIONS", True, "Enable animations in charts",
            "CHART_STYLE", "cyberpunk", "Chart style (cyberpunk, elegant, minimal)",
            "SAVE_FULL_STATS", True, "Save full statistics to file"
        )
        self.styles = {
            "cyberpunk": {
                "bg_color": "#111111",
                "text_color": "#FFFFFF",
                "grid_color": "#333333",
                "spine_color": "#9C27B0",
                "hatch": "///",
                "alpha": 0.9,
                "font": "monospace"
            },
            "elegant": {
                "bg_color": "#0A0E17",
                "text_color": "#E0E0E0",
                "grid_color": "#1F2937",
                "spine_color": "#3F51B5",
                "hatch": "",
                "alpha": 0.85,
                "font": "serif"
            },
            "minimal": {
                "bg_color": "#000000",
                "text_color": "#FFFFFF",
                "grid_color": "#222222",
                "spine_color": "#555555",
                "hatch": "",
                "alpha": 0.7,
                "font": "sans-serif"
            }
        }

    @loader.command(ru_doc="Посмотреть топ в чате")
    async def top(self, m: Message):
        """View top users by message count in the chat"""
        msg = await utils.answer(m, self.strings['loading'])
        
        client = self.client
        style = self.styles.get(self.config["CHART_STYLE"], self.styles["cyberpunk"])
        
        # Setup plot style
        plt.style.use('dark_background')
        plt.rcParams['font.family'] = style["font"]
        plt.rcParams['figure.facecolor'] = style["bg_color"]
        plt.rcParams['axes.facecolor'] = style["bg_color"]
        plt.rcParams['text.color'] = style["text_color"]
        plt.rcParams['axes.labelcolor'] = style["text_color"]
        plt.rcParams['xtick.color'] = style["text_color"]
        plt.rcParams['ytick.color'] = style["text_color"]

        # Determine chat type
        if isinstance(m.peer_id, PeerUser):
            chat_type = 'private'
            chat_id = m.peer_id.user_id
        elif isinstance(m.peer_id, PeerChat) or isinstance(m.peer_id, PeerChannel):
            chat_type = 'chat'
            chat_id = m.chat.id
        else:
            await utils.answer(m, "Unsupported chat type.")
            return

        # Process based on chat type
        if chat_type == 'chat':
            # Get all participants
            progress_msg = msg
            users = await client.get_participants(chat_id)
            users_dict = {user.id: (user.username or user.first_name) for user in users}
            
            # Count messages for each user with progress updates
            message_count = defaultdict(int)
            total_users = len(users_dict)
            
            for i, user_id in enumerate(users_dict):
                # Update progress every 5 users
                if i % 5 == 0 or i == total_users - 1:
                    progress = round((i / total_users) * 100)
                    try:
                        progress_msg = await utils.answer(
                            progress_msg, 
                            self.strings['progress'].format(progress=progress)
                        )
                    except Exception:
                        pass
                
                # Get message count for user
                result = await client(SearchRequest(
                    peer=chat_id,
                    q='',
                    filter=InputMessagesFilterEmpty(),
                    from_id=user_id,
                    limit=0,
                    min_date=None,
                    max_date=None,
                    offset_id=0,
                    add_offset=0,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))
                message_count[user_id] = result.count

            # Sort by message count
            sorted_message_count = sorted(message_count.items(), key=lambda item: item[1], reverse=True)
            
            # Generate statistics file if enabled
            if self.config["SAVE_FULL_STATS"]:
                stats_file = io.StringIO()
                stats_file.write("Username,Message Count\n")
                for user_id, count in sorted_message_count:
                    username = users_dict[user_id] or "Unknown"
                    stats_file.write(f"{username},{count}\n")
                
                stats_file.seek(0)
                stats_buf = io.BytesIO(stats_file.read().encode())
                stats_buf.name = f"{m.chat.title}_stats.csv"
                await client.send_file(
                    m.chat_id,
                    stats_buf,
                    caption=self.strings['top_file'],
                    reply_to=m.id
                )
            
            # Take top N users for visualization
            limit = self.config["TOP_LIMIT"]
            top_users = sorted_message_count[:limit]
            
            if not top_users:
                await utils.answer(m, self.strings['no_messages'])
                return
                
            usernames = [users_dict[user_id] or "Unknown" for user_id, _ in top_users]
            counts = [count for _, count in top_users]
            
            # Create visualizations
            fig = plt.figure(figsize=(12, 10), dpi=100)
            
            # Main horizontal bar chart - takes 70% of vertical space
            ax1 = plt.subplot2grid((3, 1), (0, 0), rowspan=2)
            self._create_bar_chart(ax1, usernames, counts, style)
            
            # Activity distribution chart - takes 30% of vertical space
            ax2 = plt.subplot2grid((3, 1), (2, 0))
            self._create_activity_chart(ax2, counts, style)
            
            # Add overall title and style
            fig.suptitle(
                f"{self.strings['top']} - {m.chat.title}", 
                fontsize=16, 
                color=style["text_color"], 
                fontweight='bold',
                y=0.98
            )
            
            # Tight layout with space for title
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            
            # Save figure
            buf = io.BytesIO()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                plt.savefig(buf, format='png', facecolor=style["bg_color"], bbox_inches='tight', dpi=100)
            buf.seek(0)
            
            # Prepare caption
            caption = f"{self.strings['topchat']} <b>{m.chat.title}:</b>\n\n"
            
            # Format top users with emojis and styling
            for i, (username, count) in enumerate(zip(usernames, counts)):
                if i == 0:
                    emoji = "🥇"
                elif i == 1:
                    emoji = "🥈"
                elif i == 2:
                    emoji = "🥉"
                else:
                    emoji = "▫️"
                    
                caption += f"{emoji} <b>{i+1}.</b> {username} - <i>{count}</i>\n"
                
            if len(sorted_message_count) > limit:
                caption += f"\n{self.strings['limit_exceeded'].format(limit=limit)}"
                
            # Send result
            await utils.answer_file(m, buf, caption, force_document=False)
            
        else:  # Private chat
            me = await client.get_me()
            target = await client.get_entity(chat_id)
            
            # Count messages from both participants
            my_count, their_count = await asyncio.gather(
                self._get_message_count_fast(client, chat_id, me.id),
                self._get_message_count_fast(client, chat_id, target.id)
            )
            
            # Prepare data
            message_counts = [(me.first_name, my_count), (target.first_name, their_count)]
            sorted_message_counts = sorted(message_counts, key=lambda item: item[1], reverse=True)
            
            usernames = [user for user, _ in sorted_message_counts]
            counts = [count for _, count in sorted_message_counts]
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Create bar chart
            self._create_bar_chart(ax, usernames, counts, style)
            
            # Save figure
            buf = io.BytesIO()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                plt.savefig(buf, format='png', facecolor=style["bg_color"], bbox_inches='tight', dpi=100)
            buf.seek(0)
            
            # Prepare caption
            caption = f"{self.strings['private_chat']} <b>{target.first_name}:</b>\n\n"
            total = sum(counts)
            
            for i, (username, count) in enumerate(sorted_message_counts):
                percentage = round((count / total) * 100, 1) if total > 0 else 0
                caption += f"<b>{username}</b>: {count} ({percentage}%)\n"
                
            # Send result
            await utils.answer_file(m, buf, caption, force_document=False)

    def _create_bar_chart(self, ax, labels, values, style):
        """Create a beautiful horizontal bar chart with fancy styling"""
        # Generate gradient colors
        colors = self._generate_gradient(
            self.config["GRADIENT_START"], 
            self.config["GRADIENT_END"], 
            len(labels)
        )
        
        # Create bars with rounded corners
        bars = ax.barh(labels, values, color=colors, alpha=style["alpha"], linewidth=0)
        
        # Add fancy styling to bars
        for i, bar in enumerate(bars):
            # Apply rounded corners
            x, y = bar.get_xy()
            height = bar.get_height()
            width = bar.get_width()
            
            # Apply hatch pattern if specified
            if style["hatch"]:
                bar.set_hatch(style["hatch"])
                
            # Highlight top 3
            if i < 3:
                bar.set_color(self.config["TOP_HIGHLIGHT"])
                ax.text(
                    width + max(values) * 0.02, 
                    y + height/2, 
                    f'#{i+1}', 
                    va='center', 
                    ha='left', 
                    color=self.config["TOP_HIGHLIGHT"], 
                    fontsize=12, 
                    fontweight='bold'
                )
                
            # Add value labels on bars
            ax.text(
                width - max(values) * 0.05, 
                y + height/2, 
                str(values[i]), 
                va='center', 
                ha='right', 
                color='white', 
                fontsize=10, 
                fontweight='bold',
                path_effects=[
                    plt.patheffects.withStroke(linewidth=2, foreground='black')
                ]
            )
            
        # Style the axes
        ax.set_xlabel(self.strings['msgcount'], fontsize=12, color=style["text_color"], fontweight='bold')
        ax.set_title(self.strings['top'], fontsize=14, color=style["text_color"], fontweight='bold', pad=20)
        ax.invert_yaxis()  # Highest values at the top
        
        # Style the spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(style["spine_color"])
        ax.spines['bottom'].set_color(style["spine_color"])
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.4, color=style["grid_color"], axis='x')
        
        # Add background gradient
        if self.config["CHART_STYLE"] == "cyberpunk":
            ax.set_facecolor(style["bg_color"])
            gradient = np.linspace(0, 1, 100).reshape(-1, 1)
            gradient_colors = plt.cm.Blues(gradient)
            gradient_colors[:, 3] = 0.1  # Low alpha
            ax.imshow(
                gradient, 
                extent=[0, max(values) * 1.1, -0.5, len(labels) - 0.5], 
                aspect='auto', 
                alpha=0.2, 
                origin='lower'
            )
            
        # Padding
        plt.tight_layout()
        
        return ax
        
    def _create_activity_chart(self, ax, values, style):
        """Create a chart showing the distribution of activity"""
        # Create bins for histogram
        max_val = max(values)
        bins = np.linspace(0, max_val, min(len(values), 10))
        
        # Create histogram
        n, bins, patches = ax.hist(
            values, 
            bins=bins, 
            alpha=0.7, 
            color=self.config["GRADIENT_START"],
            edgecolor='black',
            linewidth=1
        )
        
        # Style the axes
        ax.set_title(self.strings['activity_title'], fontsize=12, color=style["text_color"])
        ax.set_xlabel(self.strings['msgcount'], fontsize=10, color=style["text_color"])
        ax.set_ylabel(self.strings['activity_desc'], fontsize=10, color=style["text_color"])
        
        # Style the spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(style["spine_color"])
        ax.spines['bottom'].set_color(style["spine_color"])
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.4, color=style["grid_color"])
        
        # Add curve showing distribution trend
        if len(values) > 3:
            density = np.histogram(values, bins=20, density=True)[0]
            x = np.linspace(0, max_val, 20)
            # Smooth the curve
            smoothed = np.convolve(density, np.ones(3)/3, mode='same')
            # Scale to match histogram height
            scale_factor = max(n) / max(smoothed) if max(smoothed) > 0 else 1
            ax.plot(
                x[:-1], 
                smoothed * scale_factor, 
                color=self.config["GRADIENT_END"], 
                linewidth=2.5,
                alpha=0.8
            )
            
        return ax

    async def _get_message_count_fast(self, client, chat_id, user_id):
        """Get message count for a specific user using optimized approach"""
        total_count = 0
        offset_id = 0
        limit = 100
        total_retrieved = 0
        max_messages = 500000  # Limit for performance
        
        while total_retrieved < max_messages:
            history = await client(GetHistoryRequest(
                peer=chat_id,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0
            ))
            
            if not history.messages:
                break
                
            total_retrieved += len(history.messages)
            
            for message in history.messages:
                if message.sender_id == user_id:
                    total_count += 1
                    
            offset_id = history.messages[-1].id
            
            if len(history.messages) < limit:
                break
                
        return total_count

    def _generate_gradient(self, start_color, end_color, n):
        """Generate a gradient between two colors with n steps"""
        if n <= 1:
            return [start_color]
            
        cmap = LinearSegmentedColormap.from_list(
            'custom_gradient', 
            [start_color, end_color], 
            N=max(n, 2)
        )
        
        # Add slight randomness for visual interest
        colors = []
        for i in np.linspace(0, 1, n):
            color = list(cmap(i))
            # Add slight variation (±5%)
            for j in range(3):  # RGB channels
                color[j] = max(0, min(1, color[j] + np.random.uniform(-0.05, 0.05)))
            colors.append(tuple(color))
            
        return colors
