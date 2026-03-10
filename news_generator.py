import os
import uuid
import sys
from datetime import datetime, UTC  # Updated for timezone-aware UTC
from dotenv import load_dotenv
from supabase import create_client, Client
from google import genai

load_dotenv()

# Initialize Clients
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Fixed User ID for mandatory users_id column
FIXED_USER_ID = "cmmd0yolk0000w4i4rtj6tppe"

def generate_news_article(source_contents):
    """Generate a high-quality article by synthesizing multiple source materials."""
    try:
        print(f"Generating professional news article content from {len(source_contents)} sources...")
        
        # Format source materials for the prompt
        formatted_sources = ""
        for i, content in enumerate(source_contents, 1):
            formatted_sources += f"\n--- SOURCE MATERIAL {i} ---\n{content}\n"

        persona_prompt = (
            "You are an expert news editor for a major global publication. "
            "Your goal is to write a high-quality news article by synthesizing the provided source materials. "
            "Consolidate the information into a single, comprehensive, and cohesive story.\n\n"
            "Follow these strict journalistic rules:\n"
            "1. **Neutrality**: Objective, third-person language. No biased adjectives.\n"
            "2. **Structure**: Lead paragraph (Who, What, Where, When, Why). Inverted pyramid.\n"
            "3. **Flow**: Ensure a smooth transition between different points from multiple sources.\n"
            "4. **No Bias**: Present balanced viewpoints for controversial topics.\n\n"
            f"{formatted_sources}"
        )

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=persona_prompt
        )
        return response.text
    except Exception as e:
        return f"Gemini Error: {str(e)}"


def get_raw_articles():
    try:
        # Fetching all required fields
        response = supabase.table("raw_articles").select("id, title, content, category_id").execute()
        return response.data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []


def save_generated_article(raw_ids, title, category_id, generated_text, user_id=None):
    """Save using all mandatory columns. Falls back to FIXED_USER_ID if user_id is None."""
    try:
        new_article_id = str(uuid.uuid4())
        current_time = datetime.now(UTC).isoformat()
        
        # Use provided user_id or fall back to the constant
        final_user_id = user_id if user_id else FIXED_USER_ID

        # Primary source ID (first one in the list)
        primary_raw_id = raw_ids[0] if raw_ids else None

        data_to_insert = {
            "id": new_article_id,
            "users_id": final_user_id,
            "category_id": category_id,
            "title": title,
            "content": generated_text,
            "raw_article_id": primary_raw_id,
            "status": "generated",
            "created_at": current_time,
            "updated_at": current_time
        }

        supabase.table("content_articles").insert(data_to_insert).execute()
        print(f"[SUCCESS] Article successfully saved with ID: {new_article_id}")
        return new_article_id
    except Exception as e:
        print(f"Error saving article: {e}")
        return None


def generate_combined_article(ids, user_id=None):
    """Business logic for Next.js extension: fetches multiple raw articles and combines them."""
    if not ids:
        return {"error": "No IDs provided"}

    try:
        # Fetch articles for the provided IDs
        response = supabase.table("raw_articles").select("id, content, title, category_id").in_("id", ids).execute()
        selected_articles = response.data

        if not selected_articles:
            return {"error": "No articles found for the provided IDs"}

        # Extract contents and metadata
        source_contents = [a['content'] for a in selected_articles]
        
        # Use title of the first article as base, or generic title
        base_title = selected_articles[0].get('title', 'Combined News')
        if len(selected_articles) > 1:
            base_title = f"{base_title} (Combined)"
            
        category_id = selected_articles[0].get('category_id')

        # Generate content
        generated_content = generate_news_article(source_contents)

        if "Gemini Error:" in generated_content:
            return {"error": generated_content}

        # Save
        new_id = save_generated_article(
            raw_ids=[a['id'] for a in selected_articles],
            title=base_title,
            category_id=category_id,
            generated_text=generated_content,
            user_id=user_id
        )

        return {
            "id": new_id,
            "title": base_title,
            "content": generated_content,
            "status": "success"
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    articles = get_raw_articles()

    if not articles:
        print("No articles found in your database.")
    else:
        print("\n--- Available Articles ---")
        for a in articles:
            print(f"ID: {a['id']} | Title: {a.get('title', 'Untitled')}")

        print("\nEnter the IDs of the articles to combine (comma-separated):")
        selected_input = input("> ").strip()
        
        if not selected_input:
            print("No IDs entered. Exiting.")
            sys.exit()

        selected_ids = [s.strip() for s in selected_input.split(",")]
        
        result = generate_combined_article(selected_ids)
        
        if "error" in result:
            print(f"\n[ERROR] {result['error']}")
        else:
            print("\n--- GENERATED ARTICLE ---\n")
            print(result['content'])
            print(f"\n[SUCCESS] Article saved with ID: {result['id']}")