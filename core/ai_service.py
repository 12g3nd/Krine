import random
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

class AIContentAnalyzer:
    """
    Service for content analysis using DeepSeek-V3.2.
    """
    
    def __init__(self):
        # Qwen-0.5B-Instruct is extremely lightweight (300MB-1GB RAM) and fast
        self.model_name = "Qwen/Qwen2.5-0.5B-Instruct" 
        self.tokenizer = None
        self.model = None
        self._is_loaded = False

    def load_model(self):
        if self._is_loaded:
            return

        print(f"Loading AI Model: {self.model_name}...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, 
                trust_remote_code=True, 
                device_map="auto",
                torch_dtype=torch.float16
            )
            self._is_loaded = True
            print("AI Model loaded successfully.")
        except Exception as e:
            print(f"FAILED to load AI model: {e}")
            print("Falling back to minimal mode (keyword filtering).")
            self._is_loaded = False

    def analyze_post(self, text, image=None):
        if not self._is_loaded:
            # Lazy load on first request if not loaded
            self.load_model()
        
        if not self._is_loaded:
            return self._fallback_analyze(text)

        # Prompt engineering for DeepSeek
        prompt = f"""
        Analyze the following social media post for safety and emotion.
        
        Post Content: "{text}"
        
        Rules:
        1. Safety: Is this content safe? (No hate speech, explicit violence, severe toxicity).
        2. Tags: Generate up to 5 simple, one-word emotional or topical tags (e.g., Sad, impactful, Love).
        
        Output JSON only:
        {{
            "is_safe": true/false,
            "flag_reason": "reason if unsafe",
            "tags": ["tag1", "tag2"]
        }}
        """
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(**inputs, max_new_tokens=100)
            response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Allow for some parsing flexibility if model chatters
            # Ideally we'd use a parser, but for now let's wrap nicely
            import json
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response_text[start:end]
                result = json.loads(json_str)
                return result
                
        except Exception as e:
            print(f"AI Analysis failed: {e}")
            
        return self._fallback_analyze(text)

    def _fallback_analyze(self, text):
        # Fallback logic
        bad_words = ['nsfw', 'hate', 'kill']
        is_safe = True
        for word in bad_words:
            if word in text.lower():
                is_safe = False
                break
        
        potential_tags = ['Deep', 'Thoughts', 'Anonymous', 'Life', 'Vibes']
        tags = random.sample(potential_tags, k=3)
        
        return {
            'is_safe': is_safe,
            'flag_reason': None if is_safe else "Automated keyword flag",
            'tags': tags
        }

# Singleton
ai_analyzer = AIContentAnalyzer()
