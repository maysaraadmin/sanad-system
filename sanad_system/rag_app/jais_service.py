"""
Jais Model Service for Arabic Text Generation
Handles loading and using the Jais model for RAG answer generation
"""

import logging
import torch
from typing import List, Dict, Any, Optional
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    pipeline
)
from django.conf import settings

logger = logging.getLogger(__name__)


class JaisModelService:
    """Service for handling Jais model operations"""
    
    def __init__(self, model_name: str = "core42/jais-6b7-chat", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self._load_model()
    
    def _load_model(self):
        """Load the Jais model with quantization for local use"""
        try:
            # Configure quantization for memory efficiency
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            logger.info(f"Loading Jais model: {self.model_name}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                use_fast=True
            )
            
            # Load model with quantization
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True
            )
            
            # Create text generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map="auto",
                torch_dtype=torch.float16,
                return_full_text=False
            )
            
            logger.info("Jais model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Jais model {self.model_name}: {e}")
            # Fallback to smaller model or mock service
            self._load_fallback_model()
    
    def _load_fallback_model(self):
        """Load a fallback smaller model if Jais fails"""
        try:
            logger.info("Loading fallback multilingual model")
            fallback_model = "microsoft/DialoGPT-medium"
            
            self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
            self.model = AutoModelForCausalLM.from_pretrained(fallback_model)
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer
            )
            
            logger.info("Fallback model loaded successfully")
            
        except Exception as e2:
            logger.error(f"Failed to load fallback model: {e2}")
            # Set to None to use template-based responses
            self.pipeline = None
    
    def generate_response(self, query: str, context: List[Dict[str, Any]], max_length: int = 512) -> str:
        """Generate response using Jais model with context"""
        
        if not self.pipeline:
            return self._generate_template_response(query, context)
        
        try:
            # Format context for the model
            context_text = self._format_context_for_model(context)
            
            # Create prompt for Jais chat model
            prompt = f"""أنت مساعد متخصص في الأحاديث النبوية. استخدم الأحاديث التالية للإجابة على السؤال:

السياق:
{context_text}

السؤال: {query}

الإجابة:"""
            
            # Generate response
            responses = self.pipeline(
                prompt,
                max_new_tokens=max_length,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            if responses and len(responses) > 0:
                generated_text = responses[0]['generated_text'].strip()
                return self._clean_response(generated_text)
            
        except Exception as e:
            logger.error(f"Error generating response with Jais: {e}")
        
        return self._generate_template_response(query, context)
    
    def _format_context_for_model(self, context: List[Dict[str, Any]]) -> str:
        """Format context for the model"""
        context_parts = []
        for i, result in enumerate(context[:3], 1):  # Limit to top 3 results
            source = result.get('metadata', {}).get('source', 'مصدر غير معروف')
            text = result.get('text', '').strip()
            similarity = result.get('similarity', 0)
            
            context_parts.append(
                f"الحديث {i}: من {source} (درجة التشابه: {similarity:.2f})\n{text}"
            )
        
        return "\n\n".join(context_parts)
    
    def _clean_response(self, response: str) -> str:
        """Clean and format the generated response"""
        # Remove any prompt leakage
        if "الإجابة:" in response:
            response = response.split("الإجابة:")[-1].strip()
        
        # Remove any incomplete sentences
        if not response.endswith(('.', '؟', '!')):
            last_punct = max(
                response.rfind('.'),
                response.rfind('؟'),
                response.rfind('!')
            )
            if last_punct > 0:
                response = response[:last_punct + 1]
        
        return response
    
    def _generate_template_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Fallback template-based response"""
        context_text = "\n\n".join([
            f"المصدر: {result['metadata'].get('source', 'غير معروف')}\n"
            f"الحديث: {result['text']}\n"
            f"التشابه: {result['similarity']:.2f}"
            for result in context[:3]
        ])
        
        return f"""بناءً على البحث في قاعدة البيانات، إليك الأحاديث ذات الصلة بسؤالك "{query}":

{context_text}

ملاحظة: هذه إجابة قائمة على البحث الدلالي. يرجى التحقق من الأحاديث ومصادرها."""
    
    def is_model_loaded(self) -> bool:
        """Check if the model is properly loaded"""
        return self.pipeline is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_model_loaded(),
            "device": self.device,
            "tokenizer": self.tokenizer.__class__.__name__ if self.tokenizer else None,
            "model_type": self.model.__class__.__name__ if self.model else None
        }


# Global instance for reuse
_jais_service = None

def get_jais_service() -> JaisModelService:
    """Get or create the Jais service instance"""
    global _jais_service
    if _jais_service is None:
        _jais_service = JaisModelService()
    return _jais_service
