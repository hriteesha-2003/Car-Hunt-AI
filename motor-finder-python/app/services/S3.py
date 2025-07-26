from config import S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_URL
import boto3
from fastapi import HTTPException, UploadFile


s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# print(S3_BUCKET_NAME,"s3bckN.............")

# Upload to S3 function
def upload_to_s3(file: UploadFile ,filename: str) -> str:
    try:
        s3_key = f"car_brands/{filename}"
        s3.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": file.content_type}
        )
        return f"{S3_BUCKET_URL}/{s3_key}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload error: {str(e)}")
    

