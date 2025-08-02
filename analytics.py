import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta, date
import numpy as np

class AnalyticsManager:
    def __init__(self, session_manager, goal_manager):
        self.session_manager = session_manager
        self.goal_manager = goal_manager
    
    def generate_subject_pie_chart(self, user_id, save_path=None):
        """Generate pie chart showing study time distribution by subject"""
        subjects_data = self.session_manager.get_subject_breakdown(user_id)
        
        if not subjects_data:
            print("No study sessions found for this user.")
            return
        
        subjects = [item[0] for item in subjects_data]
        minutes = [item[1] for item in subjects_data]
        hours = [m/60 for m in minutes]  # Convert to hours
        
        plt.figure(figsize=(10, 8))
        colors = plt.cm.Set3(np.linspace(0, 1, len(subjects)))
        
        wedges, texts, autotexts = plt.pie(hours, labels=subjects, autopct='%1.1f%%', 
                                          colors=colors, startangle=90)
        
        plt.title('Study Time Distribution by Subject', fontsize=16, fontweight='bold')
        
        # Add legend with hours
        legend_labels = [f'{subject}: {hour:.1f}h' for subject, hour in zip(subjects, hours)]
        plt.legend(wedges, legend_labels, title="Subjects", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        
        plt.axis('equal')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def generate_weekly_progress_chart(self, user_id, save_path=None):
        """Generate bar chart showing weekly progress vs goals"""
        progress_data = self.goal_manager.get_weekly_progress(user_id)
        
        if not progress_data:
            print("No weekly goals found for this user.")
            return
        
        subjects = [item[0] for item in progress_data]
        targets = [item[1]/60 for item in progress_data]  # Convert to hours
        actual = [item[2]/60 for item in progress_data]   # Convert to hours
        
        x = np.arange(len(subjects))
        width = 0.35
        
        plt.figure(figsize=(12, 6))
        
        bars1 = plt.bar(x - width/2, targets, width, label='Target', color='lightblue', alpha=0.8)
        bars2 = plt.bar(x + width/2, actual, width, label='Actual', color='orange', alpha=0.8)
        
        plt.xlabel('Subjects', fontsize=12)
        plt.ylabel('Hours', fontsize=12)
        plt.title('Weekly Study Goals vs Actual Progress', fontsize=16, fontweight='bold')
        plt.xticks(x, subjects, rotation=45, ha='right')
        plt.legend()
        
        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}h', ha='center', va='bottom')
        
        for bar in bars2:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}h', ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def generate_study_timeline(self, user_id, days=30, save_path=None):
        """Generate line chart showing daily study time over specified period"""
        sessions = self.session_manager.get_user_sessions(user_id)
        
        if not sessions:
            print("No study sessions found for this user.")
            return
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(sessions, columns=['session_id', 'subject', 'duration_minutes', 
                                           'mood', 'productivity', 'notes', 'session_date', 'created_at'])
        
        # Convert session_date to datetime and filter last N days
        df['session_date'] = pd.to_datetime(df['session_date'])
        cutoff_date = datetime.now() - timedelta(days=days)
        df = df[df['session_date'] >= cutoff_date]
        
        if df.empty:
            print(f"No study sessions found in the last {days} days.")
            return
        
        # Group by date and sum duration
        daily_study = df.groupby('session_date')['duration_minutes'].sum().reset_index()
        daily_study['hours'] = daily_study['duration_minutes'] / 60
        
        plt.figure(figsize=(12, 6))
        plt.plot(daily_study['session_date'], daily_study['hours'], 
                marker='o', linewidth=2, markersize=6, color='#2E86AB')
        
        plt.fill_between(daily_study['session_date'], daily_study['hours'], 
                        alpha=0.3, color='#2E86AB')
        
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Study Hours', fontsize=12)
        plt.title(f'Daily Study Time - Last {days} Days', fontsize=16, fontweight='bold')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        # Add average line
        avg_hours = daily_study['hours'].mean()
        plt.axhline(y=avg_hours, color='red', linestyle='--', alpha=0.7, 
                   label=f'Average: {avg_hours:.1f}h')
        plt.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def generate_mood_productivity_analysis(self, user_id, save_path=None):
        """Generate charts showing mood and productivity patterns"""
        sessions = self.session_manager.get_user_sessions(user_id)
        
        if not sessions:
            print("No study sessions found for this user.")
            return
        
        df = pd.DataFrame(sessions, columns=['session_id', 'subject', 'duration_minutes', 
                                           'mood', 'productivity', 'notes', 'session_date', 'created_at'])
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Mood distribution
        mood_counts = df['mood'].value_counts()
        colors1 = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        ax1.pie(mood_counts.values, labels=mood_counts.index, autopct='%1.1f%%', 
               colors=colors1, startangle=90)
        ax1.set_title('Mood Distribution', fontsize=14, fontweight='bold')
        
        # Productivity distribution
        productivity_counts = df['productivity'].value_counts()
        colors2 = ['#FFD93D', '#6BCF7F', '#4D96FF', '#9B59B6', '#E74C3C']
        ax2.pie(productivity_counts.values, labels=productivity_counts.index, autopct='%1.1f%%', 
               colors=colors2, startangle=90)
        ax2.set_title('Productivity Distribution', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def print_study_summary(self, user_id):
        """Print comprehensive study summary"""
        total_time = self.session_manager.get_total_study_time(user_id)
        subjects_data = self.session_manager.get_subject_breakdown(user_id)
        sessions = self.session_manager.get_user_sessions(user_id, limit=10)
        
        print("\n" + "="*50)
        print("           STUDY SUMMARY REPORT")
        print("="*50)
        
        print(f"\n📊 Total Study Time: {total_time//60:.0f} hours {total_time%60:.0f} minutes")
        
        if subjects_data:
            print(f"\n📚 Subject Breakdown:")
            for subject, minutes, session_count in subjects_data:
                hours = minutes // 60
                mins = minutes % 60
                print(f"   • {subject}: {hours}h {mins}m ({session_count} sessions)")
        
        if sessions:
            print(f"\n📝 Recent Sessions:")
            for i, session in enumerate(sessions[:5], 1):
                duration_h = session[2] // 60
                duration_m = session[2] % 60
                print(f"   {i}. {session[1]} - {duration_h}h {duration_m}m "
                      f"(Mood: {session[3]}, Productivity: {session[4]}) - {session[6]}")
        
        # Weekly goals progress
        progress = self.goal_manager.get_weekly_progress(user_id)
        if progress:
            print(f"\n🎯 Weekly Goals Progress:")
            for subject, target, actual in progress:
                percentage = (actual / target * 100) if target > 0 else 0
                status = "✅" if percentage >= 100 else "⏳"
                print(f"   {status} {subject}: {actual//60}h {actual%60}m / {target//60}h {target%60}m ({percentage:.1f}%)")
        
        print("="*50)
    
    def export_data_to_csv(self, user_id, filename=None):
        """Export user's study data to CSV"""
        sessions = self.session_manager.get_user_sessions(user_id)
        
        if not sessions:
            print("No study sessions to export.")
            return
        
        df = pd.DataFrame(sessions, columns=['session_id', 'subject', 'duration_minutes', 
                                           'mood', 'productivity', 'notes', 'session_date', 'created_at'])
        
        if filename is None:
            filename = f"study_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df.to_csv(filename, index=False)
        print(f"Study data exported to: {filename}")
