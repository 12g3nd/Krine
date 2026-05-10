import random
import re
import os
import requests
import json
from transformers import pipeline

class AIContentAnalyzer:
    """
    Service for content analysis using Zero-Shot Classification.
    Model: valhalla/distilbart-mnli-12-3 (Fast & Lightweight)
    """
    
    def __init__(self):
        self.model_name = "valhalla/distilbart-mnli-12-3"
        self.classifier = None
        self._is_loaded = False
        
        # PII Regex Patterns
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        # Basic Phone: Matches 123-456-7890, (123) 456-7890, 123 456 7890
        self.phone_pattern = re.compile(r'(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}')

        # Curated list of "Vibes" for tagging
        self.candidate_labels = [
            "Nostalgic", "Hopeful", "Melancholy", "Venting", "Love", 
            "Heartbreak", "Anxious", "Peaceful", "Confession", "Regret",
            "Gratitude", "Lonely", "Inspired", "Angry", "Bittersweet",
            "Dreamy", "Lost", "Found", "Deep", "Wholesome",
            "Sad", "Happy", "Tired", "Excited", "Numb",
            "Healing", "Broken", "Growing", "Reflective", "Dark"
        ]
        
        # Safety labels to check against.
        # Added "Personal Information" and "Harassment"
        self.safety_categories = ["Safe", "Hate Speech", "Violence", "Harassment", "Personal Information"]

        # API Configuration
        self.use_api = os.getenv('USE_AI_API', 'False').lower() == 'true'
        self.api_url = "https://api-inference.huggingface.co/models/valhalla/distilbart-mnli-12-3"
        self.api_token = os.getenv('HUGGINGFACE_API_KEY')

    def load_model(self):
        if self._is_loaded:
            return

        print(f"Loading AI Model: {self.model_name}...")
        try:
            # device=-1 for CPU. This pipeline will handle tokenizer/model loading.
            self.classifier = pipeline("zero-shot-classification", model=self.model_name)
            self._is_loaded = True
            print("AI Model loaded successfully.")
        except Exception as e:
            print(f"FAILED to load AI model: {e}")
            self._is_loaded = False

    def analyze_post(self, text, image=None):
        # 1. PII Check (Regex) - Fast & Deterministic
        if self.email_pattern.search(text):
             return {
                "is_safe": False,
                "flag_reason": "Contains Email Address",
                "tags": []
            }
        
        if self.phone_pattern.search(text):
             return {
                "is_safe": False,
                "flag_reason": "Contains Phone Number",
                "tags": []
            }


        # API Path
        if self.use_api:
            if not self.api_token:
                print("WARNING: USE_AI_API is True but HUGGINGFACE_API_KEY is missing.")
                return self._fallback_analyze(text)
            return self._analyze_via_api(text)

        # Local Path
        if not self._is_loaded:
            self.load_model()
        
        if not self._is_loaded:
            return self._fallback_analyze(text)

        try:
            # 2. Safety Check (AI)
            
            safety_result = self.classifier(text, self.safety_categories, multi_label=False)
            
            # Map labels to scores
            scores = {label: score for label, score in zip(safety_result['labels'], safety_result['scores'])}
            
            safe_score = scores.get('Safe', 0.0)
            top_label = safety_result['labels'][0]
            top_score = safety_result['scores'][0]
            
            is_safe = True
            flag_reason = None
            
            # Revised Logic:
            # User wants leniency on "Hate" (venting) but strictness on "Harassment/Names".
            
            # 1. Critical Safety Floor
            # If "Safe" is extremely low, it's almost certainly bad (e.g. "I hate [Name]" was 0.02).
            if safe_score < 0.03: 
                 is_safe = False
                 flag_reason = f"Extremely Low Safety Score ({int(safe_score*100)}%)"

            # 2. Harassment Ratio Check (Catching Targeted Attacks)
            # Targeted attacks have a high Harassment-to-Safe ratio.
            # "I hate <person_name>": Harassment(0.20) / Safe(0.02) = 10.0
            # "I hate carrots":       Harassment(0.09) / Safe(0.12) = 0.75
            elif scores.get('Harassment', 0) > (safe_score * 3) and scores.get('Harassment', 0) > 0.1:
                 is_safe = False
                 flag_reason = f"Potential Harassment (Ratio {scores.get('Harassment',0)/safe_score:.1f})"

            # 3. High Confidence Checks (Standard)
            elif scores.get('Violence', 0) > 0.8:
                 is_safe = False
                 flag_reason = "Violence Detected"
            elif scores.get('Hate Speech', 0) > 0.8: # Increased from 0.4 to 0.8 for leniency
                 is_safe = False
                 flag_reason = "Hate Speech Detected"
            elif scores.get('Personal Information', 0) > 0.5: # Strict on PII
                 is_safe = False
                 flag_reason = "Personal Info Detected"

            # 3. Tagging
            # We want top 3 tags from our big list
            tag_result = self.classifier(text, self.candidate_labels, multi_label=True)
            tags = tag_result['labels'][:3]
            
            return {
                "is_safe": is_safe,
                "flag_reason": flag_reason,
                "tags": tags
            }

        except Exception as e:
            print(f"AI Analysis failed: {e}")
            return self._fallback_analyze(text)

    def _fallback_analyze(self, text):
        """
        Fallback when AI model fails to load.
        Uses basic keyword matching for safety.
        """
        # Expanded basic blocklist
        bad_words = ['hate', 'kill', 'suicide', 'death to', 'murder'] 
        is_safe = True
        
        text_lower = text.lower()
        for word in bad_words:
            if word in text_lower:
                is_safe = False
                break
        
        # If safe, return random tags, otherwise return no tags or specific flag
        tags = random.sample(self.candidate_labels, k=3) if is_safe else []
        
        return {
            'is_safe': is_safe,
            'flag_reason': None if is_safe else "Automated keyword flag (Fallback)",
            'tags': tags
        }

    def _analyze_via_api(self, text):
        """
        Analyze using HuggingFace Inference API to save RAM.
        """
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        # We need two calls: one for Safety, one for Tags.
        # Zero-shot API format usually returns scores for labels.
        
        try:
            # 1. Safety Check
            payload_safety = {
                "inputs": text,
                "parameters": {"candidate_labels": self.safety_categories}
            }
            response = requests.post(self.api_url, headers=headers, json=payload_safety)
            
            if response.status_code != 200:
                print(f"API Error (Safety): {response.status_code} - {response.text}")
                # If model is loading (503), we might want to retry, but for now fallback.
                return self._fallback_analyze(text)
                
            safety_data = response.json()
            # safety_data is generic, might be dict or list depending on endpoint version.
            # Usually: {'sequence': '...', 'labels': [...], 'scores': [...]}
            
            if 'labels' not in safety_data:
                 print(f"API Unexpected Response: {safety_data}")
                 return self._fallback_analyze(text)
                 
            scores = {label: score for label, score in zip(safety_data['labels'], safety_data['scores'])}

            safe_score = scores.get('Safe', 0.0)
            
            is_safe = True
            flag_reason = None
            
            # Reusing original logic
            if safe_score < 0.03: 
                 is_safe = False
                 flag_reason = f"Extremely Low Safety Score ({int(safe_score*100)}%)"
            elif scores.get('Harassment', 0) > (safe_score * 3) and scores.get('Harassment', 0) > 0.1:
                 is_safe = False
                 flag_reason = f"Potential Harassment"
            elif scores.get('Violence', 0) > 0.8:
                 is_safe = False
                 flag_reason = "Violence Detected"
            elif scores.get('Hate Speech', 0) > 0.8:
                 is_safe = False
                 flag_reason = "Hate Speech Detected"
            elif scores.get('Personal Information', 0) > 0.5:
                 is_safe = False
                 flag_reason = "Personal Info Detected"

            # 2. Tagging (only if safe, or independent?)
            # Let's get tags anyway
            payload_tags = {
                "inputs": text,
                "parameters": {"candidate_labels": self.candidate_labels}
            }
            response_tags = requests.post(self.api_url, headers=headers, json=payload_tags)
             
            tags = []
            if response_tags.status_code == 200:
                tag_data = response_tags.json()
                if 'labels' in tag_data:
                    tags = tag_data['labels'][:3]
            
            return {
                "is_safe": is_safe,
                "flag_reason": flag_reason,
                "tags": tags
            }

        except Exception as e:
            print(f"API Request Failed: {e}")
            return self._fallback_analyze(text)

    def analyze_and_tag_post_background(self, post_id):
        """
        Background task to analyze post and update DB.
        """
        try:
            # Import here to avoid circular imports
            from .models import Post, Tag
            
            try:
                post = Post.objects.get(id=post_id)
            except Post.DoesNotExist:
                return

            # Run Analysis
            result = self.analyze_post(post.content, post.image)
            
            # Apply Safety Flag
            if not result['is_safe']:
                post.is_flagged = True
                post.save()
            
            # Apply Tags
            for tag_name in result['tags']:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                post.tags.add(tag)
            
            # Mark analysis as complete so it shows up in feed
            post.is_analyzed = True
            post.save()
                
            print(f"Background Analysis Complete for Post {post_id}")
            
        except Exception as e:
            print(f"Background Task Failed: {e}")

# Singleton
ai_analyzer = AIContentAnalyzer()
