import os
import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables. LLM functionality will be disabled.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"
    
    async def generate_dsl_from_description(self, description: str, swagger_docs: str = None, api_endpoints: List[str] = None) -> Dict[str, Any]:
        if not self.client:
            return {
                "dsl_script": "",
                "status": "error",
                "error": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            }
        
        try:
            system_prompt = self._get_system_prompt()
            api_info = ""
            if swagger_docs:
                api_info += f"\n\nSwagger dokumentacija:\n{swagger_docs[:2000]}..."  # Ograniči na 2000 znakova
            if api_endpoints:
                api_info += f"\n\nDostupni API endpoint-i:\n" + "\n".join(api_endpoints)
            
            user_prompt = f"""
            Generiraj DSL skriptu za sljedeći user journey opis:
            
            {description}
            
            {api_info}
            
            Generiraj kompletnu DSL skriptu koja uključuje:
            1. Osnovne parametre (users, duration, pattern)
            2. User journey definicije s odgovarajućim HTTP metodama
            3. Realistične API endpoint-ove i payload-ove (koristi dostupne endpoint-e)
            4. Odgovarajući workload pattern za opisani scenarij
            
            Odgovori SAMO s DSL skriptom, bez dodatnih objašnjenja.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            dsl_script = response.choices[0].message.content.strip()
            
            return {
                "dsl_script": dsl_script,
                "status": "success",
                "model_used": self.model
            }
            
        except Exception as e:
            logger.error(f"Error generating DSL from description: {e}")
            return {
                "dsl_script": "",
                "status": "error",
                "error": str(e)
            }
    
    async def optimize_existing_dsl(self, dsl_script: str, optimization_goal: str = "improve performance") -> Dict[str, Any]:
        if not self.client:
            return {
                "optimized_dsl": dsl_script,
                "explanation": "",
                "status": "error",
                "error": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            }
        
        try:
            system_prompt = self._get_optimization_system_prompt()
            user_prompt = f"""
            Optimiziraj sljedeći DSL na temelju cilja: {optimization_goal}
            
            Postojeći DSL:
            ```dsl
            {dsl_script}
            ```
            
            Tvoja zadaća:
            1. Analiziraj postojeći DSL
            2. Predloži poboljšanja za {optimization_goal}
            3. Generiraj optimiziranu verziju
            4. Objasni ključne promjene
            
            Odgovori s optimiziranim DSL-om i kratkim objašnjenjem promjena.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content.strip()
            
            if "```dsl" in result:
                parts = result.split("```dsl")
                if len(parts) > 1:
                    dsl_part = parts[1].split("```")[0].strip()
                    explanation = parts[0].strip() + (parts[1].split("```")[1] if "```" in parts[1] else "")
                else:
                    dsl_part = result
                    explanation = ""
            else:
                dsl_part = result
                explanation = ""
            
            return {
                "optimized_dsl": dsl_part,
                "explanation": explanation,
                "status": "success",
                "model_used": self.model
            }
            
        except Exception as e:
            logger.error(f"Error optimizing DSL: {e}")
            return {
                "optimized_dsl": dsl_script,
                "explanation": "",
                "status": "error",
                "error": str(e)
            }
    
    def _get_system_prompt(self):
        return """
        Ti si ekspert za generiranje DSL skripti za testiranje performansi web aplikacija.
        
        Tvoja zadaća je generirati valjane DSL skripte koje:
        1. Definiraju user journey-e s realističnim API pozivima
        2. Koriste odgovarajuće HTTP metode (GET, POST, PUT, DELETE, PATCH)
        3. Uključuju realistične payload-ove za POST/PUT zahtjeve
        4. Koriste prikladne workload pattern-e (steady, burst, ramp_up, daily_cycle, spike, gradual_ramp)
        5. Definiraju razumne brojeve korisnika i trajanje testa
        
        Format DSL-a:
        - users: [broj] - broj simuliranih korisnika
        - duration: [broj] - trajanje u sekundama
        - pattern: [pattern_name] - uzorak opterećenja
        - journey: [ime] - ime user journey-a
        - repeat: [broj] - broj ponavljanja (opcionalno)
        - - [METHOD] [path] [payload] - korak u journey-u
        - end - kraj journey-a
        
        Primjer:
        users: 10
        duration: 300
        pattern: steady
        
        journey: ecommerce_flow
        repeat: 2
        - GET /api/products
        - POST /api/cart {"product_id": 123, "quantity": 1}
        - GET /api/cart
        - POST /api/checkout {"payment_method": "credit_card"}
        end
        """
    
    def _get_optimization_system_prompt(self):
        return """
        Ti si ekspert za optimizaciju DSL skripti za testiranje performansi.
        
        Tvoja zadaća je analizirati postojeći DSL i predložiti poboljšanja za:
        - Povećanje performansi testa
        - Realističnije user journey-e
        - Bolje workload pattern-e
        - Optimizaciju broja korisnika i trajanja
        - Dodavanje validacijskih koraka
        
        Uvijek zadrži osnovnu strukturu DSL-a i dodaj samo smislene poboljšanja.
        """
llm_service = LLMService()
