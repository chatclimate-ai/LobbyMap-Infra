from fastapi import FastAPI, HTTPException, status
import os
from motor.motor_asyncio import AsyncIOMotorClient
from .schema import FeedbackResponseModel, EvidenceModel, FeedbackCollection
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()


class FeedbackToolServer:
    def __init__(self):
        self.app = FastAPI(
            title="API to process feedback for the Lobby Map System",
            description="""
            This API processes the feedback collected from the users of the Lobby Map System, 
            It collects feedback on the retrieved evidences from the RAG system and stores it in the database
            for later analysis.
            The are 4 main endpoints:
            - POST /feedback/ : The feedback collected on the evidence is stored in the database.
            - GET /feedback/ : To retrieve all the evidences stored in the database.
            - GET /feedback/{feedback_id} : To retrieve a specific evidence by its id.
             
            """,
            version="0.0.1",
            lifespan=self.lifespan,
        )
        self.mongo_uri = os.getenv("MONGODB_URI", "mongodb://lobbymap:lobbymap_pass@mongodb/feedback_db?retryWrites=true&w=majority")
        self.db_name = os.getenv("MONGO_INITDB_DATABASE", "feedback_db")
        self.client = None
        self.db = None
        self._add_middlewares()
        self._add_routes()

        # Add startup and shutdown event handlers
        # self.app.on_event("startup")(self.connect_to_mongo)
        # self.app.on_event("shutdown")(self.close_mongo_connection)

    def _add_middlewares(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _add_routes(self):
        @self.app.post(
            "/feedback/",
            response_description="Generate a new feedback on a given evidence.",
            response_model=FeedbackResponseModel,
            status_code=status.HTTP_201_CREATED,
        )
        async def create_feedback(feedback: EvidenceModel):
            feedback_dict = feedback.dict()
            evidence = await self.db.feedback_collection.insert_one(feedback_dict)
            created_feedback = await self.db.feedback_collection.find_one({"_id": evidence.inserted_id})
            return self.feedback_helper(created_feedback)

        @self.app.get("/feedback/", response_model=FeedbackCollection)
        async def get_feedback():
            feedbacks = []
            async for feedback in self.db.feedback_collection.find():
                feedbacks.append(self.feedback_helper(feedback))
            return FeedbackCollection(feedbacks=feedbacks)

        @self.app.get("/feedback/{feedback_id}", response_model=FeedbackResponseModel)
        async def get_feedback_by_id(feedback_id: str):
            if (
                feedback := await self.db.feedback_collection.find_one({"_id": feedback_id})
            ) is not None:
                return self.feedback_helper(feedback)

            raise HTTPException(status_code=404, detail="Feedback not found")

        @self.app.delete("/feedback", response_model=dict)
        async def delete_all_feedback():
            """Deletes all feedback objects from the feedback_collection."""
            delete_result = await self.db.feedback_collection.delete_many({})

            if delete_result.deleted_count > 0:
                return {"message": f"Deleted {delete_result.deleted_count} feedback items."}

            return {"message": "No feedback items found to delete."}

    @staticmethod
    def feedback_helper(feedback: dict) -> dict:
        """
        Converts a MongoDB document into a dictionary that matches the Pydantic model structure.
        """
        return {
            "id": str(feedback["_id"]),
            "search_elements": {
                "searched_query": feedback["search_elements"]["searched_query"],
                "searched_author": feedback["search_elements"].get("searched_author"),
                "searched_date": feedback["search_elements"].get("searched_date"),
                "searched_region": feedback["search_elements"].get("searched_region"),
                "searched_file_name": feedback["search_elements"].get("searched_file_name"),
                "top_k": feedback["search_elements"]["top_k"],
            },
            "artifacts": {
                "parser": {
                    "model_name": feedback["artifacts"]["parser"]["model_name"],
                    "options": feedback["artifacts"]["parser"].get("options"),
                },
                "rag_components": {
                    "chunking_method": feedback["artifacts"]["rag_components"]["chunking_method"],
                    "chunking_similarity_threshold": feedback["artifacts"]["rag_components"]["chunking_similarity_threshold"],
                    "vectorizer_model_name": feedback["artifacts"]["rag_components"]["vectorizer_model_name"],
                    "reranker_model_name": feedback["artifacts"]["rag_components"]["reranker_model_name"],
                },
            },
            "pdf_doc_name": feedback["pdf_doc_name"],
            "content": feedback["content"],
            "author": feedback.get("author"),
            "date": feedback.get("date"),
            "region": feedback.get("region"),
            "rank": feedback["rank"],
            "status": feedback["status"],
            "confidence_score": feedback["confidence_score"],
            "rank_score": feedback["rank_score"],
            "generated_stance": feedback["generated_stance"],
            "generated_stance_reason": feedback["generated_stance_reason"],
            "generated_stance_score": feedback["generated_stance_score"],
            "updated_rank": feedback["updated_rank"],
            "updated_status": feedback.get("updated_status"),
            "updated_generated_stance": feedback.get("updated_generated_stance"),
            "timestamp": feedback["timestamp"],
        }

    # async def connect_to_mongo(self):
    #     self.client = AsyncIOMotorClient(self.mongo_uri)
    #     self.db = self.client[self.db_name]

    # async def close_mongo_connection(self):
    #     self.client.close()

    async def lifespan(self, app: FastAPI):
        # Startup: Connect to MongoDB
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        yield
        # Shutdown: Close MongoDB connection
        self.client.close()


# Instantiate the class and get the FastAPI app
feedback_api = FeedbackToolServer()
app = feedback_api.app
